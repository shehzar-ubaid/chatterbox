import sys
import os
import traceback
import base64
import tempfile
import scipy.io.wavfile as wavfile
import numpy as np

print("1. Container started, starting Infinity Clone worker...")
sys.stdout.flush()

# RunPod Import Check
try:
    import runpod
    print("2. RunPod library successfully imported.")
except Exception as e:
    print(f"CRITICAL ERROR: RunPod import fail ho gaya: {e}")
    sys.exit(1)

# Source folder path add kiya
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

model = None
try:
    print("3. Model load ho raha hai...")
    
    from chatterbox import Chatterbox 
    
    # FIX 1: Theek tareeqay se model load karna (from_local use kar kay)
    device = "cuda" # RunPod par GPU available hota hay
    model_path = "./models" # Agar models kisi aur folder mein hain toh yeh path change karein
    
    model = Chatterbox.from_local(model_path, device)
    
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
        
        # FIX 2: Sahi tareeqay se audio generate karna
        # (Yahan 'voice_id' nahi, balkay generate function text leta hay)
        audio_tensor = model.generate(text=text)
        
        # Tensor ko numpy array mein convert karna taake file mein save ho sakay
        audio_numpy = audio_tensor.squeeze().cpu().numpy()
        
        # Temporary file mein audio save karna
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            wavfile.write(temp_wav_path, model.sr, audio_numpy)
        
        # Base64 mein convert karna
        with open(temp_wav_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')
            
        # Cleanup temporary file
        os.remove(temp_wav_path)

        return {
            "status": "success",
            "audio_base64": audio_base64
        }
    except Exception as e:
        return {"error": str(e), "traceback": traceback.format_exc()}

print("5. Starting RunPod Serverless handler...")
sys.stdout.flush()
runpod.serverless.start({"handler": process_audio})