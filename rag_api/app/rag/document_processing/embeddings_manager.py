# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

import logging
import torch
from sentence_transformers import SentenceTransformer
from langchain_core.embeddings import Embeddings
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

_instance = None


class EmbeddingsManager:
    """Manages sentence-transformers embeddings"""

    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        config_path = Path(__file__).parents[2] / "config" / "config.yaml"
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        emb_cfg = cfg["document_processing"]["embeddings"]

        self.device = "cuda" if emb_cfg.get("use_gpu", True) and torch.cuda.is_available() else "cpu"
        self.model_name = emb_cfg["model_name"]
        self.hf_token = emb_cfg.get("hf_token")
        logger.info(f"Loading embeddings model '{self.model_name}' on device '{self.device}'")
        self.model = self._load_model()

    def _load_model(self):
        try:
            return SentenceTransformer(self.model_name, device=self.device)
        except Exception as e:
            logger.warning(
                f"Direct load of '{self.model_name}' failed: {e}. "
                "Falling back to HuggingFace snapshot download..."
            )
            from huggingface_hub import snapshot_download
            path = snapshot_download(self.model_name, token=self.hf_token)
            return SentenceTransformer(path, device=self.device)

    def get_langchain_embeddings(self) -> Embeddings:
        model = self.model
        class Adapter(Embeddings):
            def embed_documents(self, texts):
                return model.encode(texts, convert_to_numpy=True).tolist()
            def embed_query(self, text):
                return model.encode([text], convert_to_numpy=True).tolist()[0]
        return Adapter()
