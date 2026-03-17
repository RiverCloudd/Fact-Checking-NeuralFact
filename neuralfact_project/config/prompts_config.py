"""
Prompts Configuration for Fact-Checking
Quản lý các prompt template cho hệ thống kiểm chứng sự thật
"""
import yaml
import os

class PromptConfig:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "prompts_vi.yaml")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.prompts = yaml.safe_load(f)
    
    @property
    def decompose_prompt(self) -> str:
        return self.prompts.get('decompose_prompt', '')
    
    @property
    def checkworthy_prompt(self) -> str:
        return self.prompts.get('checkworthy_prompt', '')
    
    @property
    def qgen_prompt(self) -> str:
        return self.prompts.get('qgen_prompt', '')
    
    @property
    def verify_prompt(self) -> str:
        return self.prompts.get('verify_prompt', '')


# Global prompt config instance
prompt_config = PromptConfig()

__all__ = ['PromptConfig', 'prompt_config']

