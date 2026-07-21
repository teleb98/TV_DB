"""
임베더 추상화 — 라인업 positioning 을 벡터로.
기본: model2vec 정적 다국어 임베딩(torch 불필요, 빠름).
폴백: 해시 기반 결정론 임베더(오프라인·의존성 0, 파이프라인 검증용).
운영에서 Voyage/OpenAI 등으로 바꾸려면 encode()만 같은 시그니처로 교체.
"""
from __future__ import annotations
import re
import hashlib
import numpy as np

DEFAULT_MODEL = "minishlab/potion-multilingual-128M"


def _l2(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=1, keepdims=True)
    n[n == 0] = 1.0
    return v / n


class Model2VecEmbedder:
    """model2vec 정적 임베딩. 코사인 검색용으로 L2 정규화."""
    def __init__(self, model_name: str = DEFAULT_MODEL):
        from model2vec import StaticModel
        self.model = StaticModel.from_pretrained(model_name)
        self.name = model_name
        self.dim = int(self.model.encode(["dim probe"]).shape[1])

    def encode(self, texts: list[str]) -> np.ndarray:
        v = np.asarray(self.model.encode(list(texts)), dtype=np.float32)
        return _l2(v)


class HashEmbedder:
    """해시 기반 결정론 임베더(폴백). 단어+한글 bigram 해시 → 고정차원."""
    name = "hash-256"
    dim = 256

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in self._tokens(t):
                h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
                out[i, h % self.dim] += 1.0
        return _l2(out)

    @staticmethod
    def _tokens(t: str) -> list[str]:
        words = re.findall(r"[0-9a-z]+|[가-힣]+", (t or "").lower())
        grams: list[str] = []
        for w in words:
            grams.append(w)
            for j in range(len(w) - 1):     # 한글 bigram (형태소 근사)
                grams.append(w[j:j + 2])
        return grams


def get_embedder(model_name: str = DEFAULT_MODEL):
    """model2vec 우선, 실패 시 해시 폴백."""
    try:
        return Model2VecEmbedder(model_name)
    except Exception as e:
        print(f"[embed] model2vec 로드 실패({type(e).__name__}: {str(e)[:60]}) → 해시 폴백")
        return HashEmbedder()
