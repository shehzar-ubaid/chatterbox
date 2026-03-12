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
    print("2. RunPod library successfully imported.")
except Exception as e:
    print(f"CRITICAL ERROR: RunPod import fail ho gaya: {e}")
    sys.exit(1)

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

model = None
try:
    print("3. Model load ho raha hai (Pehli dafa heavy files internet se download hongi, isme 2-3 minute lag saktay hain)...")
    from chatterbox import Chatterbox 
    
    # FIX: Khud ba khud internet se original weights download karega
    model = Chatterbox.from_pretrained("cuda")
    
    print("4. Model VRAM mein load ho gaya!")
except Exception as e:
    print("ERROR: Model load hotay waqt masla aya:")
    print(traceback.format_exc())

def process_audio(job):
    job_input = job.get('input', {})
    text = job_input.get('text', 'Hello from Infinity Clone')
    
    try:
        print(f"Processing job ID: {job.get('id')}")
        if model is None:
             return {"error": "API failed. Model theek say load nahi hua."}
        
        audio_tensor = model.generate(text=text)
        audio_numpy = audio_tensor.squeeze().cpu().numpy()
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            wavfile.write(temp_wav_path, model.sr, audio_numpy)
        
        with open(temp_wav_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
            
        os.remove(temp_wav_path)
        return {"status": "success", "audio_base64": audio_base64}
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

print("5. Starting RunPod Serverless handler...")
sys.stdout.flush()
runpod.serverless.start({"handler": process_audio})