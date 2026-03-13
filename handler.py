import sys
import os
import traceback
import base64
import tempfile
import scipy.io.wavfile as wavfile
import numpy as np

print("1. Container started, starting Infinity Clone worker...")
sys.stdout.flush()

try:
    import runpod
    import torch
    print("2. RunPod library successfully imported.")
except Exception as e:
    print(f"CRITICAL ERROR: RunPod import fail ho gaya: {e}")
    sys.exit(1)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Dono models (TTS aur V2V) ko globally define kar rahay hain
tts_model = None
vc_model = None

try:
    print("3. Models load ho rahay hain (Pehli dafa heavy files internet se download hongi)...")
    from chatterbox import ChatterboxTTS, ChatterboxVC 
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 1. TTS aur Voice Cloning ka model load karein
    print("TTS Model loading...")
    tts_model = ChatterboxTTS.from_pretrained(device)
    
    # 2. Voice to Voice (V2V) ka model load karein
    print("V2V Model loading...")
    try:
        vc_model = ChatterboxVC.from_pretrained(device)
    except Exception as vc_e:
        print(f"Note: V2V model load hotay waqt warning aayi (yeh normal ho sakti hay): {vc_e}")
    
    print("4. Models VRAM mein successfully load ho gaye!")
except Exception as e:
    print("ERROR: Model load hotay waqt masla aya:")
    print(traceback.format_exc())

# Base64 audio ko temporary .wav file mein save karne ka function
def decode_base64_to_temp(b64_string, suffix=".wav"):
    if not b64_string:
        return None
    # Agar frontend se header (data:audio/wav;base64,) sath aaye toh usay hata dein
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
        
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_file.write(base64.b64decode(b64_string))
    temp_file.close()
    return temp_file.name

def process_audio(job):
    job_input = job.get('input', {})
    
    # Frontend se aane wali action check karein (tts, clone, ya v2v)
    action = job_input.get('action', 'tts')
    
    try:
        print(f"Processing job ID: {job.get('id')} - Action: {action}")
        
        audio_tensor = None
        sr = 24000 # Default sample rate
        
        # =========== 1. TTS aur VOICE CLONING ===========
        if action in ['tts', 'clone']:
            if tts_model is None:
                 return {"error": "API failed. TTS Model theek say load nahi hua."}
            
            text = job_input.get('text', 'Hello from Infinity Clone')
            speaker_wav_b64 = job_input.get('speaker_wav')
            
            kwargs = {}
            temp_speaker_path = None
            
            # Agar frontend ne sample voice bheji hay (Cloning kay liye)
            if speaker_wav_b64:
                temp_speaker_path = decode_base64_to_temp(speaker_wav_b64)
                kwargs['audio_prompt_path'] = temp_speaker_path
            
            # Advance settings jo frontend se ayengi
            if 'temperature' in job_input: kwargs['temperature'] = float(job_input['temperature'])
            if 'speed' in job_input: kwargs['speed'] = float(job_input['speed'])
            if 'repetition_penalty' in job_input: kwargs['repetition_penalty'] = float(job_input['repetition_penalty'])
            if 'top_p' in job_input: kwargs['top_p'] = float(job_input['top_p'])
            
            # Audio Generate karein
            audio_tensor = tts_model.generate(text=text, **kwargs)
            sr = tts_model.sr if hasattr(tts_model, 'sr') else 24000
            
            # Server ki memory bachane kay liye temp file delete karein
            if temp_speaker_path:
                os.remove(temp_speaker_path)
                
        # =========== 2. VOICE TO VOICE (V2V) ===========
        elif action == 'v2v':
            if vc_model is None:
                return {"error": "API failed. V2V Model load nahi hua."}
                
            source_audio_b64 = job_input.get('source_audio')
            target_audio_b64 = job_input.get('target_audio')
            
            if not source_audio_b64 or not target_audio_b64:
                return {"error": "V2V kay liye 'source_audio' aur 'target_audio' dono zaroori hain."}
            
            # Dono files ko temp files mein save karein
            temp_source = decode_base64_to_temp(source_audio_b64)
            temp_target = decode_base64_to_temp(target_audio_b64)
            
            # V2V Generate karein
            audio_tensor = vc_model.generate(audio=temp_source, target_voice_path=temp_target)
            sr = vc_model.sr if hasattr(vc_model, 'sr') else 24000
            
            # Temp files delete karein
            os.remove(temp_source)
            os.remove(temp_target)
            
        else:
            return {"error": f"Unknown action received: {action}"}
        
        # =========== RESULT KO WAPIS BASE64 MEIN BADALNA ===========
        if audio_tensor is not None:
            # Agar result tuple ho toh pehla hissa nikal lein
            if isinstance(audio_tensor, tuple):
                audio_tensor = audio_tensor[0]
                
            audio_numpy = audio_tensor.squeeze().cpu().numpy()
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
                wavfile.write(temp_wav_path, sr, audio_numpy)
            
            with open(temp_wav_path, "rb") as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
                
            os.remove(temp_wav_path)
            return {"status": "success", "audio_base64": audio_base64}
        else:
            return {"error": "Generation failed. Audio tensor is None."}
            
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

print("5. Starting RunPod Serverless handler...")
sys.stdout.flush()
runpod.serverless.start({"handler": process_audio})