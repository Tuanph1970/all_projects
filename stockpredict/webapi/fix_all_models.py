#!/usr/bin/env python3
"""
Script to fix model save/load directory structure issues across all model classes.

This script adds:
1. model_storage_dir initialization in __init__
2. Proper train() method with clean directory structure
3. Enhanced save_model() and load_model() methods
"""

import os
import re

# List of all models to fix
MODELS_TO_FIX = [
    'RNNPredictModel.py',
    'NHitsPredictModel.py',
    'NBeatsPredictModel.py',
    'TransformerPredictModel.py',
    'TFTPredictModel.py',
    'TCNPredictModel.py',
    'DLinearPredictModel.py',
    'NLinearPredictModel.py',
    'TimeDeepEncoderPredictModel.py',
    'CatBoostPredictModel.py',
    'LightGBMPredictModel.py',
    'RandomForestPredictModel.py',
    'XGBoostPredictModel.py',
]

MODELS_DIR = '/home/tuanph/TuanPH/stockpredict/webapi/Models'

def add_storage_dir_to_init(content):
    """Add model_storage_dir initialization after self.output_chunk_length or similar"""

    # Find the last self.xxx = assignment in __init__ before self.model =
    pattern = r'(        self\.\w+ = [^\n]+\n)(        self\.model = )'

    storage_dir_code = '''
        # Define model storage directory
        self.model_storage_dir = os.path.join(os.getcwd(), 'saved_models')
        os.makedirs(self.model_storage_dir, exist_ok=True)

'''

    replacement = r'\1' + storage_dir_code + r'\2'
    content = re.sub(pattern, replacement, content)

    return content

def fix_train_method(content, model_class_name):
    """Fix the train() method to use clean directory structure"""

    # Pattern to match the entire train method
    pattern = r'    def train\(self,\s*id\):\s*\n.*?(?=\n    def |\nclass |\Z)'

    # New train method template
    new_train = '''    def train(self, id):
        """
        Train the model and save it to a clean directory structure.

        Directory structure:
        /webapi/saved_models/solution_{id}.pt

        Args:
            id: Solution ID used as the model filename
        """
        # Set work_dir to None to prevent Darts from creating nested directories
        # Darts will use default 'darts_logs' directory for training checkpoints
        self.model.work_dir = None

        print(f"\\n[TRAIN] Starting model training for solution ID: {id}")
        print(f"[TRAIN] Model storage directory: {self.model_storage_dir}")

        # Train the model
        self.model.fit(
            self.train_target,
            past_covariates=self.past_train_multi if hasattr(self, 'past_train_multi') else None,
            future_covariates=self.future_train_multi if hasattr(self, 'future_train_multi') else None,
            val_series=self.val_target,
            val_past_covariates=self.past_val_multi if hasattr(self, 'past_val_multi') else None,
            val_future_covariates=self.future_val_multi if hasattr(self, 'future_val_multi') else None,
            verbose=True
        )

        # Save model to clean path structure
        model_filename = f"solution_{id}.pt"
        model_path = os.path.join(self.model_storage_dir, model_filename)

        print(f"[TRAIN] Saving model to: {model_path}")
        self.model.save(model_path)
        print(f"[TRAIN] Model saved successfully!")

        return model_path
'''

    content = re.sub(pattern, new_train, content, flags=re.DOTALL)

    return content

def fix_save_model_method(content):
    """Fix the save_model() method"""

    pattern = r'    def save_model\(self,.*?\n.*?(?=\n    def |\nclass |\Z)'

    new_save_model = '''    def save_model(self, file_name, user_model_name):
        """
        Save model configuration to a clean directory structure.

        Directory structure:
        /webapi/saved_models/{file_name}

        Args:
            file_name: Name of the model file (e.g., "model_123.pt")
            user_model_name: User-defined model name (stored in model metadata)
        """
        # Ensure saved_models directory exists
        os.makedirs(self.model_storage_dir, exist_ok=True)

        # Build full path
        model_path = os.path.join(self.model_storage_dir, file_name)

        # Update model parameters
        self.model.model_name = user_model_name

        # Update all model parameters based on current instance variables
        for param_name in ['input_chunk_length', 'output_chunk_length', 'hidden_dim',
                           'n_rnn_layers', 'dropout', 'batch_size', 'n_epochs',
                           'training_length', 'num_stacks', 'num_blocks', 'num_layers',
                           'layer_widths', 'd_model', 'nhead', 'num_encoder_layers',
                           'num_decoder_layers', 'dim_feedforward', 'lags']:
            if hasattr(self, param_name):
                param_value = getattr(self, param_name)
                if param_name in self.model.model_params:
                    if isinstance(param_value, (int, float)):
                        self.model.model_params[param_name] = type(self.model.model_params[param_name])(param_value)
                    else:
                        self.model.model_params[param_name] = param_value

        # Update learning rate
        if 'optimizer_kwargs' in self.model.model_params and hasattr(self, 'learning_rate'):
            self.model.model_params.get('optimizer_kwargs')['lr'] = float(self.learning_rate)

        print(f"[SAVE_MODEL] Saving to: {model_path}")
        print(f"[SAVE_MODEL] User model name: {user_model_name}")

        # Save the model
        self.model.save(model_path)

        print(f"[SAVE_MODEL] Model saved successfully!")
        return model_path
'''

    content = re.sub(pattern, new_save_model, content, flags=re.DOTALL)

    return content

def fix_load_model_method(content, model_class_name):
    """Fix the load_model() method"""

    pattern = r'    def load_model\(self,.*?\n.*?(?=\n    def |\nclass |\Z)'

    new_load_model = f'''    def load_model(self, path):
        """
        Load a saved model from disk.

        Args:
            path: Full path to the model file or just the filename (will look in saved_models/)

        Returns:
            Loaded model instance
        """
        # If only filename provided, construct full path
        if not os.path.isabs(path):
            path = os.path.join(self.model_storage_dir, path)

        print(f"[LOAD_MODEL] Loading model from: {{path}}")

        # Check if file exists
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {{path}}")

        # Load the model - import the appropriate model class
        from darts.models.forecasting.{model_class_name.lower().replace('predictmodel', '_model')} import {model_class_name.replace('PredictModel', 'Model')}
        model = {model_class_name.replace('PredictModel', 'Model')}.load(path=path)

        # Extract all available model parameters
        param_mapping = {{
            'model': 'model_sub_type',
            'model_type': 'model_sub_type',
        }}

        for model_param, instance_attr in param_mapping.items():
            if model_param in model.model_params:
                setattr(self, instance_attr, model.model_params[model_param])

        # Direct parameter extraction
        for param_name in ['input_chunk_length', 'output_chunk_length', 'hidden_dim',
                           'n_rnn_layers', 'dropout', 'batch_size', 'n_epochs',
                           'training_length', 'num_stacks', 'num_blocks', 'num_layers',
                           'layer_widths', 'd_model', 'nhead', 'num_encoder_layers',
                           'num_decoder_layers', 'dim_feedforward', 'lags']:
            if param_name in model.model_params:
                setattr(self, param_name, model.model_params.get(param_name))

        # Extract learning rate
        if 'optimizer_kwargs' in model.model_params:
            self.learning_rate = model.model_params['optimizer_kwargs'].get('lr')

        # Set the loaded model
        self.model = model

        print(f"[LOAD_MODEL] Model loaded successfully!")
        print(f"[LOAD_MODEL] Model type: {{getattr(self, 'model_sub_type', 'N/A')}}")
        print(f"[LOAD_MODEL] Input chunk length: {{getattr(self, 'input_chunk_length', 'N/A')}}")
        print(f"[LOAD_MODEL] Output chunk length: {{getattr(self, 'output_chunk_length', 'N/A')}}")

        return model
'''

    content = re.sub(pattern, new_load_model, content, flags=re.DOTALL)

    return content

def fix_model_file(model_filename):
    """Apply all fixes to a single model file"""

    filepath = os.path.join(MODELS_DIR, model_filename)

    print(f"\n{'='*60}")
    print(f"Processing: {model_filename}")
    print(f"{'='*60}")

    # Read the file
    with open(filepath, 'r') as f:
        content = f.read()

    # Extract model class name
    model_class_name = model_filename.replace('.py', '')

    # Apply fixes
    original_content = content

    # 1. Add storage directory initialization
    if 'self.model_storage_dir' not in content:
        print("  [1/4] Adding model_storage_dir initialization...")
        content = add_storage_dir_to_init(content)
    else:
        print("  [1/4] model_storage_dir already exists, skipping...")

    # 2. Fix train method
    if 'self.model.work_dir = self.model.model_name' in content:
        print("  [2/4] Fixing train() method...")
        content = fix_train_method(content, model_class_name)
    else:
        print("  [2/4] train() method already fixed, skipping...")

    # 3. Fix save_model method
    if 'os.path.join(path,user_model_name)' in content or 'os.path.join(path, user_model_name)' in content:
        print("  [3/4] Fixing save_model() method...")
        content = fix_save_model_method(content)
    else:
        print("  [3/4] save_model() method already fixed, skipping...")

    # 4. Fix load_model method
    print("  [4/4] Fixing load_model() method...")
    content = fix_load_model_method(content, model_class_name)

    # Write back if changed
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✅ {model_filename} updated successfully!")
    else:
        print(f"  ⏭️  {model_filename} - no changes needed")

    return content != original_content

def main():
    """Main function to fix all models"""

    print("\n" + "="*60)
    print("MODEL SAVE/LOAD FIX SCRIPT")
    print("="*60)
    print(f"\nFound {len(MODELS_TO_FIX)} models to process\n")

    updated_count = 0
    skipped_count = 0

    for model_filename in MODELS_TO_FIX:
        try:
            was_updated = fix_model_file(model_filename)
            if was_updated:
                updated_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"  ❌ ERROR processing {model_filename}: {str(e)}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"  Total models: {len(MODELS_TO_FIX)}")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped (already fixed): {skipped_count}")
    print(f"  Failed: {len(MODELS_TO_FIX) - updated_count - skipped_count}")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
