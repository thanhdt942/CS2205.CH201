import os
from hydra import compose, initialize
from omegaconf import DictConfig
import dacite
from src.conf.structure import AppConfig
from dotenv import load_dotenv

load_dotenv()

def load_config() -> AppConfig:
    initialize(version_base=None, config_path="src/conf")
    dict_cfg = compose(config_name="config")
    
    config_obj = dacite.from_dict(
        data_class=AppConfig, 
        data=dict_cfg,
        config=dacite.Config(cast=[int, float, bool])
    )
    return config_obj

cfg = load_config()

print("Configuration loaded successfully.")
