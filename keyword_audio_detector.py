"""Optional Wav2Vec2/XLS-R audio keyword classifier for Bad Word Beep."""
from pathlib import Path

import numpy as np
import torch
from transformers import AutoFeatureExtractor, Wav2Vec2Model

LABELS = ['blaka', 'gamw', 'malaka', 'mounopano', 'skata', 'negative']
MODEL_ID = 'facebook/wav2vec2-xls-r-300m'


class SpeechHead(torch.nn.Module):
    def __init__(self, dimension):
        super().__init__()
        self.project = torch.nn.Conv1d(dimension, 64, 1)
        self.context = torch.nn.Conv1d(64, 64, 5, padding=2)
        self.head = torch.nn.Sequential(
            torch.nn.Dropout(0.4),
            torch.nn.Linear(128, len(LABELS)),
        )

    def forward(self, x, mask):
        valid = mask[:, :, 0, :]
        x = torch.relu(self.project(x[:, 0])) * valid
        x = torch.relu(self.context(x)) * valid
        mean = x.sum(-1) / valid.sum(-1).clamp_min(1)
        maximum = x.masked_fill(valid == 0, -1e9).amax(-1)
        return self.head(torch.cat([mean, maximum], dim=1))


class AudioKeywordDetector:
    def __init__(self, model_dir, threshold=0.65):
        self.model_dir = Path(model_dir)
        self.threshold = float(threshold)
        checkpoint = torch.load(
            self.model_dir / 'model.pt',
            map_location='cpu',
            weights_only=True,
        )
        config = checkpoint['config']
        if config['labels'] != LABELS:
            raise ValueError('Checkpoint label order mismatch')
        self.processor = AutoFeatureExtractor.from_pretrained(
            MODEL_ID,
            cache_dir=str(self.model_dir / 'pretrained'),
        )
        self.encoder = Wav2Vec2Model.from_pretrained(
            MODEL_ID,
            cache_dir=str(self.model_dir / 'pretrained'),
        )
        self.encoder.eval()
        self.encoder.requires_grad_(False)
        self.head = SpeechHead(config['dimension'])
        self.head.load_state_dict(checkpoint['state_dict'])
        self.head.eval()
        self.mean = checkpoint['mean']
        self.std = checkpoint['std']

    @torch.inference_mode()
    def detect(self, audio):
        audio = np.asarray(audio, dtype=np.float32)
        if audio.ndim != 1 or len(audio) != 32000:
            raise ValueError('Audio window must be exactly 32000 mono samples')
        inputs = self.processor(
            audio,
            sampling_rate=16000,
            return_tensors='pt',
        )
        result = self.encoder(
            **inputs,
            output_hidden_states=True,
            return_dict=True,
        )
        feature = torch.stack(result.hidden_states[-4:]).mean(0)[0].T.contiguous()
        feature = (feature - self.mean) / self.std
        x = feature.unsqueeze(0)
        mask = torch.ones(1, 1, 1, x.shape[-1])
        probabilities = torch.softmax(self.head(x, mask)[0], dim=-1)
        target_probabilities = probabilities[:-1]
        negative_probability = float(probabilities[-1])
        best = int(torch.argmax(target_probabilities))
        score = float(target_probabilities[best])
        if score > negative_probabilities if False else score > negative_probability and score >= self.threshold:
            return LABELS[best], score
        return None, score
