"""
Классы нейросетевых архитектур.

Для каждой архитектуры есть:
- класс с явным __init__(self, **config),
- атрибут CONFIG_KEYS — список обязательных ключей конфига,
- метод forward.

Контракт: для тренировки и инференса модель принимает float32-тензор
shape (batch_size, n_features) и возвращает либо реконструкцию (AE),
либо логиты (классификаторы).
"""

from __future__ import annotations

import torch
import torch.nn as nn


class TabularAutoencoder(nn.Module):
    """Симметричный fully-connected автоэнкодер для табличных данных.

    Архитектура:
        encoder: input_dim -> hidden_dims[0] -> hidden_dims[1] -> ... -> bottleneck_dim
        decoder: bottleneck_dim -> ... -> hidden_dims[0] -> input_dim

    На выходе декодера — линейная активация (для восстановления значений,
    которые могут быть отрицательными после RobustScaler).
    """

    CONFIG_KEYS = ["input_dim", "hidden_dims", "bottleneck_dim",
                   "leaky_slope", "dropout"]

    def __init__(self,
                 input_dim: int,
                 hidden_dims: list[int],
                 bottleneck_dim: int,
                 leaky_slope: float = 0.1,
                 dropout: float = 0.0):
        super().__init__()
        self.input_dim       = input_dim
        self.hidden_dims     = list(hidden_dims)
        self.bottleneck_dim  = bottleneck_dim
        self.leaky_slope     = leaky_slope
        self.dropout         = dropout

        # Encoder: input_dim -> hidden_dims[0] -> ... -> bottleneck_dim
        enc_layers: list[nn.Module] = []
        prev_dim = input_dim
        for h in hidden_dims:
            enc_layers.append(nn.Linear(prev_dim, h))
            enc_layers.append(nn.LeakyReLU(leaky_slope))
            if dropout > 0:
                enc_layers.append(nn.Dropout(dropout))
            prev_dim = h
        enc_layers.append(nn.Linear(prev_dim, bottleneck_dim))
        # Activation на bottleneck тоже LeakyReLU — иначе градиенты не текут
        enc_layers.append(nn.LeakyReLU(leaky_slope))
        self.encoder = nn.Sequential(*enc_layers)

        # Decoder: bottleneck_dim -> hidden_dims (в обратном порядке) -> input_dim
        dec_layers: list[nn.Module] = []
        prev_dim = bottleneck_dim
        for h in reversed(hidden_dims):
            dec_layers.append(nn.Linear(prev_dim, h))
            dec_layers.append(nn.LeakyReLU(leaky_slope))
            if dropout > 0:
                dec_layers.append(nn.Dropout(dropout))
            prev_dim = h
        dec_layers.append(nn.Linear(prev_dim, input_dim))
        # На выходе — без активации (linear)
        self.decoder = nn.Sequential(*dec_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x)
        x_hat = self.decoder(z)
        return x_hat

    def get_config(self) -> dict:
        return {
            "input_dim":      self.input_dim,
            "hidden_dims":    self.hidden_dims,
            "bottleneck_dim": self.bottleneck_dim,
            "leaky_slope":    self.leaky_slope,
            "dropout":        self.dropout,
        }

class TabularMLP(nn.Module):
    """Fully-connected MLP для бинарной классификации табличных данных.

    Архитектура:
        input -> [Linear -> BatchNorm1d -> ReLU -> Dropout] × N -> Linear -> 1 logit

    Выходной слой возвращает **логит** (без sigmoid). Для получения
    вероятности применить torch.sigmoid внутри inference.
    """

    CONFIG_KEYS = ["input_dim", "hidden_dims", "dropout"]

    def __init__(self,
                 input_dim: int,
                 hidden_dims: list[int],
                 dropout: float = 0.2):
        super().__init__()
        self.input_dim   = input_dim
        self.hidden_dims = list(hidden_dims)
        self.dropout     = dropout

        layers: list[nn.Module] = []
        prev_dim = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev_dim, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU(inplace=True))
            if dropout > 0:
                layers.append(nn.Dropout(dropout))
            prev_dim = h
        # Output head: один логит
        layers.append(nn.Linear(prev_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Возвращает логит формы (batch_size, 1). При loss используем
        # BCEWithLogitsLoss, который сам применяет sigmoid внутри.
        return self.net(x)

    def get_config(self) -> dict:
        return {
            "input_dim":   self.input_dim,
            "hidden_dims": self.hidden_dims,
            "dropout":     self.dropout,
        }
    
class _FeatureTokenizer(nn.Module):
    """Превращает (B, n_features) -> (B, n_features, d_token)."""

    def __init__(self, n_features: int, d_token: int):
        super().__init__()
        self.n_features = n_features
        self.d_token    = d_token
        # Веса формы (n_features, d_token): для каждой фичи свой вектор
        self.weights = nn.Parameter(torch.empty(n_features, d_token))
        self.biases  = nn.Parameter(torch.empty(n_features, d_token))
        # Инициализация по Kaiming, как в rtdl
        nn.init.kaiming_uniform_(self.weights, a=5**0.5)
        nn.init.kaiming_uniform_(self.biases.unsqueeze(0), a=5**0.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, n_features) -> (B, n_features, 1) * (n_features, d_token) + bias
        # -> (B, n_features, d_token)
        return x.unsqueeze(-1) * self.weights + self.biases


class _CLSToken(nn.Module):
    """Добавляет обучаемый CLS-токен в начало последовательности."""

    def __init__(self, d_token: int):
        super().__init__()
        self.token = nn.Parameter(torch.empty(1, 1, d_token))
        nn.init.kaiming_uniform_(self.token, a=5**0.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, n_features, d_token) -> (B, n_features+1, d_token)
        batch_size = x.shape[0]
        cls_expanded = self.token.expand(batch_size, -1, -1)
        return torch.cat([cls_expanded, x], dim=1)


class _TransformerBlock(nn.Module):
    """Один блок: MultiheadAttention -> FFN, с pre-LayerNorm."""

    def __init__(self, d_token: int, n_heads: int, ffn_hidden: int,
                 attn_dropout: float, ffn_dropout: float):
        super().__init__()
        self.norm1 = nn.LayerNorm(d_token)
        self.attn  = nn.MultiheadAttention(
            embed_dim=d_token, num_heads=n_heads,
            dropout=attn_dropout, batch_first=True,
        )
        self.norm2 = nn.LayerNorm(d_token)
        self.ffn   = nn.Sequential(
            nn.Linear(d_token, ffn_hidden),
            nn.GELU(),
            nn.Dropout(ffn_dropout),
            nn.Linear(ffn_hidden, d_token),
            nn.Dropout(ffn_dropout),
        )

    def forward(self, x: torch.Tensor,
                return_attention: bool = False) -> torch.Tensor:
        # Pre-LayerNorm: norm перед attention/ffn, residual после
        x_norm = self.norm1(x)
        attn_out, attn_weights = self.attn(x_norm, x_norm, x_norm,
                                            need_weights=return_attention,
                                            average_attn_weights=True)
        x = x + attn_out
        x = x + self.ffn(self.norm2(x))
        if return_attention:
            return x, attn_weights
        return x


class TabularFTTransformer(nn.Module):
    """FT-Transformer для табличной бинарной классификации.

    Архитектура по Gorishniy et al. (2021), упрощённая для нашего use case
    (только numerical features, без category embeddings).

    Pipeline:
      input (B, n_features) ->
      FeatureTokenizer -> (B, n_features, d_token) ->
      CLSToken -> (B, n_features+1, d_token) ->
      [TransformerBlock] × n_blocks ->
      выход CLS-токена (B, d_token) ->
      Linear -> 1 logit
    """

    CONFIG_KEYS = ["n_features", "d_token", "n_blocks", "n_heads",
                   "ffn_hidden", "attn_dropout", "ffn_dropout"]

    def __init__(self,
                 n_features: int,
                 d_token: int = 32,
                 n_blocks: int = 2,
                 n_heads: int = 4,
                 ffn_hidden: int = 128,
                 attn_dropout: float = 0.2,
                 ffn_dropout: float = 0.1):
        super().__init__()
        self.n_features   = n_features
        self.d_token      = d_token
        self.n_blocks     = n_blocks
        self.n_heads      = n_heads
        self.ffn_hidden   = ffn_hidden
        self.attn_dropout = attn_dropout
        self.ffn_dropout  = ffn_dropout

        assert d_token % n_heads == 0, \
            f"d_token={d_token} must be divisible by n_heads={n_heads}"

        self.tokenizer = _FeatureTokenizer(n_features, d_token)
        self.cls       = _CLSToken(d_token)
        self.blocks    = nn.ModuleList([
            _TransformerBlock(d_token, n_heads, ffn_hidden,
                              attn_dropout, ffn_dropout)
            for _ in range(n_blocks)
        ])
        self.head_norm = nn.LayerNorm(d_token)
        self.head      = nn.Linear(d_token, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.tokenizer(x)         # (B, n_features, d_token)
        x = self.cls(x)                # (B, n_features+1, d_token)
        for block in self.blocks:
            x = block(x)
        cls_repr = self.head_norm(x[:, 0])   # CLS-выход — первый токен
        return self.head(cls_repr)            # (B, 1) logits

    @torch.no_grad()
    def get_attention_maps(self, x: torch.Tensor) -> list[torch.Tensor]:
        """Возвращает attention карты со всех блоков. Для интерпретации."""
        self.eval()
        x = self.tokenizer(x)
        x = self.cls(x)
        maps = []
        for block in self.blocks:
            x, attn_w = block(x, return_attention=True)
            maps.append(attn_w)   # (B, n_features+1, n_features+1)
        return maps

    def get_config(self) -> dict:
        return {
            "n_features":   self.n_features,
            "d_token":      self.d_token,
            "n_blocks":     self.n_blocks,
            "n_heads":      self.n_heads,
            "ffn_hidden":   self.ffn_hidden,
            "attn_dropout": self.attn_dropout,
            "ffn_dropout":  self.ffn_dropout,
        }