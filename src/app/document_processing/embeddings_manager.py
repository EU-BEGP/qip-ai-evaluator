import torch
from sentence_transformers import SentenceTransformer
from langchain.embeddings.base import Embeddings
import yaml
from pathlib import Path

class EmbeddingsManager:
    """Manages sentence-transformers embeddings"""

    def __init__(self):
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)
        emb_cfg = cfg["document_processing"]["embeddings"]

        self.device = "cuda" if emb_cfg.get("use_gpu", True) and torch.cuda.is_available() else "cpu"
        self.model_name = emb_cfg["model_name"]
        self.hf_token = emb_cfg.get("hf_token")
        self.model = self._load_model()

    def _load_model(self):
        try:
            return SentenceTransformer(self.model_name, device=self.device)
        except Exception:
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
