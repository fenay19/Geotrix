"""
GeoTrade AI — CNN-BiGRU-Attention Sequence Model (Phase 4)
===========================================================
Architecture upgrades over Phase 3:
  • Stacked Conv1D encoder  : 5 → 64ch → 64ch (BN + GELU + Dropout)
  • Deeper BiGRU            : 128 hidden, 2 layers, internal dropout
  • Multi-Head Attention    : 4 heads over full 256-dim GRU output
  • Projection head         : 256 → 128 → 32 (GELU + Dropout)
  • Output embedding dim    : 32  (was 16)

Training upgrades:
  • FocalLoss(gamma=2)      — focuses on hard SELL minority examples
  • CosineAnnealingLR       — smoother convergence than flat lr
  • WeightedRandomSampler   — oversamples SELL in every batch
  • Gradient clipping       — max_norm=1.0 for stability
  • 50 epochs + patience=10 early stopping (was 25 epochs, no scheduler)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pandas as pd
from torch.utils.data import TensorDataset, DataLoader, WeightedRandomSampler


# ── Focal Loss ────────────────────────────────────────────────────────────────

class FocalLoss(nn.Module):
    """
    Multi-class Focal Loss.
    Reduces relative loss for well-classified examples and focuses
    training on hard, misclassified examples (especially minority SELL class).

    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    """
    def __init__(self, gamma: float = 2.0, weight=None, reduction: str = "mean"):
        super().__init__()
        self.gamma     = gamma
        self.weight    = weight      # per-class weighting tensor
        self.reduction = reduction

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        # log-softmax for numerical stability
        log_prob   = F.log_softmax(logits, dim=1)
        prob       = torch.exp(log_prob)

        # Gather the log-prob and prob for the true class
        log_pt = log_prob.gather(1, targets.unsqueeze(1)).squeeze(1)
        pt     = prob.gather(1, targets.unsqueeze(1)).squeeze(1)

        # Focal modulation factor
        focal_factor = (1.0 - pt) ** self.gamma
        loss = -focal_factor * log_pt

        # Apply per-class weights if provided
        if self.weight is not None:
            wt   = self.weight.to(logits.device)
            loss = loss * wt[targets]

        if self.reduction == "mean":
            return loss.mean()
        elif self.reduction == "sum":
            return loss.sum()
        return loss


# ── Sequence Model (Embedder) ─────────────────────────────────────────────────

class SequenceModel(nn.Module):
    """
    Phase 4 Sequence Embedder:
    Raw OHLCV Window (30, 5) → Stacked Conv1D → Deep BiGRU → Multi-Head Attention → 32D Embedding

    Input shape : (batch, seq_len=30, input_dim=5)
    Output shape: (batch, embed_dim=32)
    """

    def __init__(self, input_dim: int = 5, embed_dim: int = 32):
        super().__init__()
        self.embed_dim = embed_dim

        # ── CNN Encoder (stacked 1D convolutions) ──────────────────────────
        # Conv1D expects (batch, channels, seq_len)
        self.conv1 = nn.Conv1d(input_dim, 64, kernel_size=3, padding=1)
        self.bn1   = nn.BatchNorm1d(64)
        self.conv2 = nn.Conv1d(64, 64, kernel_size=3, padding=1)
        self.bn2   = nn.BatchNorm1d(64)
        self.cnn_drop = nn.Dropout(0.20)

        # ── Bidirectional GRU (2 layers) ───────────────────────────────────
        # input: (batch, seq_len, 64); output: (batch, seq_len, 256)
        self.gru = nn.GRU(
            input_size  = 64,
            hidden_size = 128,
            num_layers  = 2,
            batch_first = True,
            bidirectional = True,
            dropout     = 0.20,      # applied between GRU layers
        )

        # ── Multi-Head Attention ───────────────────────────────────────────
        # 4 heads over 256-dim (128 fwd + 128 bwd) GRU output
        self.attn = nn.MultiheadAttention(
            embed_dim   = 256,
            num_heads   = 4,
            dropout     = 0.10,
            batch_first = True,
        )
        self.attn_norm = nn.LayerNorm(256)

        # ── Projection Head: 256 → 128 → embed_dim ────────────────────────
        self.fc1      = nn.Linear(256, 128)
        self.proj_drop = nn.Dropout(0.30)
        self.fc2      = nn.Linear(128, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            embedding: (batch, embed_dim)
        """
        # 1. CNN Encoder
        # x: (batch, seq_len, C) → transpose → (batch, C, seq_len)
        out = x.transpose(1, 2)
        out = F.gelu(self.bn1(self.conv1(out)))
        out = F.gelu(self.bn2(self.conv2(out)))
        out = self.cnn_drop(out)
        # transpose back: (batch, seq_len, 64)
        out = out.transpose(1, 2)

        # 2. BiGRU (2 layers)
        # out: (batch, seq_len, 256)
        out, _ = self.gru(out)

        # 3. Multi-Head Self-Attention with residual + LayerNorm
        attn_out, _ = self.attn(out, out, out)
        out = self.attn_norm(out + attn_out)   # residual connection

        # 4. Global average pooling over sequence dimension
        context = out.mean(dim=1)              # (batch, 256)

        # 5. Projection head
        emb = F.gelu(self.fc1(context))
        emb = self.proj_drop(emb)
        emb = self.fc2(emb)                    # (batch, embed_dim)
        return emb


# ── Classifier Wrapper (for pre-training) ────────────────────────────────────

class SequenceClassifier(nn.Module):
    """
    Thin 3-class head on top of SequenceModel for supervised pre-training.
    After training, only the SequenceModel backbone is saved and re-used
    for feature extraction.
    """
    def __init__(self, seq_model: SequenceModel, num_classes: int = 3):
        super().__init__()
        self.seq_model = seq_model
        self.out_layer = nn.Linear(seq_model.embed_dim, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        emb    = self.seq_model(x)
        logits = self.out_layer(emb)
        return logits


# ── Sliding Window Preprocessing ──────────────────────────────────────────────

def create_sequence_dataset(
    df: pd.DataFrame,
    seq_len: int = 30,
    target_col: str = "label",
    le=None,
):
    """
    Builds sliding window sequences from a DataFrame containing OHLCV data.

    Returns:
        X_seq        : np.ndarray  (num_samples, seq_len, 5) — normalized OHLCV windows
        y            : np.ndarray  (num_samples,)            — encoded labels, or None
        valid_indices: list of timestamps for each sequence's last day
    """
    required = ["open", "high", "low", "close", "volume"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    closes    = df["close"].values
    opens     = df["open"].values
    highs     = df["high"].values
    lows      = df["low"].values
    volumes   = df["volume"].values
    timestamps = df.index

    X_seq, y, valid_indices = [], [], []

    for i in range(seq_len - 1, len(df)):
        s = i - seq_len + 1

        w_close  = closes[s : i + 1]
        w_open   = opens[s : i + 1]
        w_high   = highs[s : i + 1]
        w_low    = lows[s : i + 1]
        w_vol    = volumes[s : i + 1]

        # Price normalization: relative to first-day close of window
        ref_price  = w_close[0] if w_close[0] != 0 else 1.0
        norm_close = w_close / ref_price - 1.0
        norm_open  = w_open  / ref_price - 1.0
        norm_high  = w_high  / ref_price - 1.0
        norm_low   = w_low   / ref_price - 1.0

        # Volume normalization: relative to window mean volume
        mean_vol  = np.mean(w_vol)
        norm_vol  = w_vol / (mean_vol + 1e-6)

        # Stack: (seq_len, 5)  columns = [open, high, low, close, volume]
        seq = np.column_stack([norm_open, norm_high, norm_low, norm_close, norm_vol])
        X_seq.append(seq)
        valid_indices.append(timestamps[i])

        if target_col in df.columns:
            val = df[target_col].iloc[i]
            y.append(val)

    X_seq = np.array(X_seq, dtype=np.float32)

    if len(y) > 0:
        y = np.array(y)
        if le is not None:
            y = le.transform(y)
        return X_seq, y, valid_indices

    return X_seq, None, valid_indices


# ── Training Function ─────────────────────────────────────────────────────────

def train_sequence_model(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_valid: np.ndarray,
    y_valid: np.ndarray,
    num_classes: int = 3,
    epochs: int = 50,
    batch_size: int = 64,
    focal_gamma: float = 2.0,
    patience: int = 10,
) -> SequenceModel:
    """
    Trains SequenceClassifier on (X_train, y_train) with:
      - FocalLoss(gamma=focal_gamma) with per-class weighting (SELL boosted 2×)
      - CosineAnnealingLR scheduler
      - WeightedRandomSampler to oversample minority SELL class
      - Gradient clipping (max_norm=1.0)
      - Early stopping (patience=10 on validation loss)

    Returns:
        best_model: SequenceModel with weights from the best validation checkpoint.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  [SeqModel] Training on {device} | "
          f"train={len(X_train)} valid={len(X_valid)} "
          f"epochs={epochs} batch={batch_size} gamma={focal_gamma}")

    # ── Model ──────────────────────────────────────────────────────────────
    seq_model  = SequenceModel(input_dim=5, embed_dim=32)
    classifier = SequenceClassifier(seq_model, num_classes=num_classes).to(device)

    # ── Per-class weights: upweight SELL (class index varies by LabelEncoder) ─
    counts     = np.bincount(y_train, minlength=num_classes).astype(float)
    total      = counts.sum()
    cls_weight = torch.tensor(
        [total / (num_classes * max(c, 1)) for c in counts],
        dtype=torch.float32,
    )
    # Extra 2× boost for SELL (assume class 2 = SELL after LabelEncoder sort BUY/HOLD/SELL)
    # We find the SELL index dynamically as the class with fewest samples
    sell_idx = int(np.argmin(counts))
    cls_weight[sell_idx] *= 2.0
    print(f"  [SeqModel] Class weights: {cls_weight.tolist()}  (SELL idx={sell_idx})")

    criterion = FocalLoss(gamma=focal_gamma, weight=cls_weight)

    # ── Optimizer + Scheduler ──────────────────────────────────────────────
    optimizer = torch.optim.Adam(classifier.parameters(), lr=1e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=1e-5)

    # ── WeightedRandomSampler (oversample SELL in every batch) ────────────
    sample_weights = np.array([1.0 / max(counts[c], 1) for c in y_train], dtype=np.float32)
    # Give SELL 3× the base oversampling weight
    sample_weights[y_train == sell_idx] *= 3.0
    sampler = WeightedRandomSampler(
        weights     = torch.from_numpy(sample_weights),
        num_samples = len(X_train),
        replacement = True,
    )

    # ── DataLoaders ────────────────────────────────────────────────────────
    train_ds = TensorDataset(
        torch.tensor(X_train),
        torch.tensor(y_train, dtype=torch.long),
    )
    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler)

    val_ds = TensorDataset(
        torch.tensor(X_valid),
        torch.tensor(y_valid, dtype=torch.long),
    )
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False)

    # ── Training Loop ──────────────────────────────────────────────────────
    best_val_loss  = float("inf")
    best_state     = None
    patience_count = 0

    for epoch in range(epochs):
        # -- Train --
        classifier.train()
        train_loss = 0.0
        for bx, by in train_loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            logits = classifier(bx)
            loss   = criterion(logits, by)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(classifier.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * bx.size(0)
        train_loss /= len(train_loader.dataset)

        # -- Validate --
        classifier.eval()
        val_loss = 0.0
        with torch.no_grad():
            for bx, by in val_loader:
                bx, by = bx.to(device), by.to(device)
                logits = classifier(bx)
                loss   = criterion(logits, by)
                val_loss += loss.item() * bx.size(0)
        val_loss /= len(val_loader.dataset)

        scheduler.step()

        # -- Early stopping --
        if val_loss < best_val_loss:
            best_val_loss  = val_loss
            best_state     = {k: v.cpu().clone() for k, v in classifier.seq_model.state_dict().items()}
            patience_count = 0
        else:
            patience_count += 1

        if (epoch + 1) % 10 == 0 or epoch == 0 or patience_count == 0:
            lr_now = scheduler.get_last_lr()[0]
            print(f"  [SeqModel] Epoch {epoch+1:3d}/{epochs} | "
                  f"train={train_loss:.4f}  val={val_loss:.4f}  "
                  f"lr={lr_now:.2e}  patience={patience_count}/{patience}")

        if patience_count >= patience:
            print(f"  [SeqModel] Early stopping at epoch {epoch+1} (patience={patience})")
            break

    print(f"  [SeqModel] Done. Best val loss: {best_val_loss:.4f}")

    # ── Return best backbone ───────────────────────────────────────────────
    best_model = SequenceModel(input_dim=5, embed_dim=32)
    best_model.load_state_dict(best_state)
    return best_model
