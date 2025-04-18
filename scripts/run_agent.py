# run_agent.py
from sfx_agent.config import Config
import logging

def main():
    cfg = Config("configs/sfx_agent.yml")
    logging.basicConfig(level=cfg._cfg["logging"]["level"])
    print("✔ ElevenLabs voice:", cfg.eleven_voice)
    print("✔ ElevenLabs model:", cfg.eleven_model)
    print("✔ Gemma model:", cfg.gemma_model)
    print("✔ Output folder:", cfg.output_folder)
    print("✔ Default duration:", cfg.default_duration)
    print("✔ Batch influences:", cfg.batch_influences)

if __name__ == "__main__":
    main()
