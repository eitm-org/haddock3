"""Test module."""
from pathlib import Path


tests_path = Path(__file__).resolve().parents[0]
golden_data = Path(tests_path, 'golden_data')

configs_data = Path(tests_path, 'configs')
emptycfg = Path(configs_data, 'empty.cfg')
haddock3_yaml_cfg_examples = Path(configs_data, 'yml_example.yml')
haddock3_yaml_converted = Path(configs_data, 'yaml2cfg_converted.cfg')

params_data = Path(tests_path, 'params')
emscoring_default_params = Path(params_data, 'default_emscoring.yaml')
mdscoring_default_params = Path(params_data, 'default_mdscoring.yaml')
