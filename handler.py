import sys
import os
import traceback
import base64
import tempfile
import scipy.io.wavfile as wavfile
import numpy as np
import inspect
import re

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

tts_model = None
vc_model = None

try:
    print("3. Models load ho rahay hain...")
    from chatterbox import ChatterboxTTS, ChatterboxVC 
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    print("TTS Model loading...")
    tts_model = ChatterboxTTS.from_pretrained(device)
    
    print("V2V Model loading (using TTS engine)...")
    vc_model = ChatterboxVC(s3gen=tts_model.s3gen, device=device)
    
    print("4. Models VRAM mein successfully load ho gaye!")
except Exception as e:
    print("ERROR: Model load hotay waqt masla aya:")
    print(traceback.format_exc())

def decode_base64_to_temp(b64_string, suffix=".wav"):
    if not b64_string:
        return None
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
        
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_file.write(base64.b64decode(b64_string))
    temp_file.close()
    return temp_file.name

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 0]

def process_audio(job):
    job_input = job.get('input', {})
    action = job_input.get('action', 'tts')
    
    try:
        print(f"Processing job ID: {job.get('id')} - Action: {action}")
        
        audio_numpy_final = None
        sr = 24000 
        
        # =========== 1. TTS aur VOICE CLONING ===========
        if action in ['tts', 'clone']:
            if tts_model is None:
                 return {"error": "API failed. TTS Model theek say load nahi hua."}
            
            full_text = job_input.get('text', 'Hello from Infinity Clone')
            speaker_wav_b64 = job_input.get('speaker_wav')
            
            kwargs = {}
            temp_speaker_path = None
            valid_keys = inspect.signature(tts_model.generate).parameters.keys()
            
            if speaker_wav_b64:
                temp_speaker_path = decode_base64_to_temp(speaker_wav_b64)
                if 'voice' in valid_keys: kwargs['voice'] = temp_speaker_path
                elif 'audio_prompt_path' in valid_keys: kwargs['audio_prompt_path'] = temp_speaker_path
                elif 'speaker' in valid_keys: kwargs['speaker'] = temp_speaker_path
            
            if 'temperature' in job_input and 'temperature' in valid_keys: kwargs['temperature'] = float(job_input['temperature'])
            if 'speed' in job_input and 'speed' in valid_keys: kwargs['speed'] = float(job_input['speed'])
            if 'repetition_penalty' in job_input and 'repetition_penalty' in valid_keys: kwargs['repetition_penalty'] = float(job_input['repetition_penalty'])
            if 'top_p' in job_input and 'top_p' in valid_keys: kwargs['top_p'] = float(job_input['top_p'])
            
            sentences = split_into_sentences(full_text)
            audio_chunks = []
            
            for i, sentence in enumerate(sentences):
                audio_tensor = tts_model.generate(text=sentence, **kwargs)
                if isinstance(audio_tensor, tuple):
                    audio_tensor = audio_tensor[0]
                
                # BULLETPROOF TENSOR/NUMPY CHECK
                if hasattr(audio_tensor, 'cpu'):
                    chunk_numpy = audio_tensor.squeeze().cpu().numpy()
                else:
                    chunk_numpy = np.squeeze(audio_tensor)
                    
                audio_chunks.append(chunk_numpy)
            
            if not audio_chunks:
                 return {"error": "Koi text process nahi ho saka."}
            
            audio_numpy_final = np.concatenate(audio_chunks)
            sr = tts_model.sr if hasattr(tts_model, 'sr') else 24000
            
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
            
            temp_source = decode_base64_to_temp(source_audio_b64)
            temp_target = decode_base64_to_temp(target_audio_b64)
            
            vc_valid_keys = inspect.signature(vc_model.generate).parameters.keys()
            vc_kwargs = {}
            
            if 'target_voice_path' in vc_valid_keys: vc_kwargs['target_voice_path'] = temp_target
            elif 'voice' in vc_valid_keys: vc_kwargs['voice'] = temp_target
                
            print("Generating V2V audio...")
            audio_tensor = vc_model.generate(audio=temp_source, **vc_kwargs)
            
            if isinstance(audio_tensor, tuple):
                audio_tensor = audio_tensor[0]
                
            # BULLETPROOF TENSOR/NUMPY CHECK FOR V2V
            if hasattr(audio_tensor, 'cpu'):
                audio_numpy_final = audio_tensor.squeeze().cpu().numpy()
            else:
                audio_numpy_final = np.squeeze(audio_tensor)
                
            sr = vc_model.sr if hasattr(vc_model, 'sr') else 24000
            
            os.remove(temp_source)
            os.remove(temp_target)
            
        else:
            return {"error": f"Unknown action received: {action}"}
        
        # =========== RESULT KO WAPIS BHEJNA ===========
        if audio_numpy_final is not None:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                temp_wav_path = temp_wav.name
                wavfile.write(temp_wav_path, sr, audio_numpy_final)
            
            with open(temp_wav_path, "rb") as audio_file:
                audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
                
            os.remove(temp_wav_path)
            print("Job successfully completed!")
            return {"status": "success", "audio_base64": audio_base64}
        else:
            return {"error": "Generation failed. Audio is None."}
            
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

print("5. Starting RunPod Serverless handler...")
sys.stdout.flush()
runpod.serverless.start({"handler": process_audio})