"""Export TorchScript courier_weights.pt to a numpy .npz file."""
import sys, os
import torch
import numpy as np

weights_path = os.path.join("app", "services", "courier_weights.pt")
model = torch.jit.load(weights_path, map_location="cpu")
model.eval()

state = {}
for name, param in model.named_parameters():
    state[name] = param.detach().cpu().numpy()
for name, buf in model.named_buffers():
    state[name] = buf.detach().cpu().numpy()

print("Extracted parameters:")
for k, v in state.items():
    print(f"  {k}: {v.shape} {v.dtype}")

out_path = os.path.join("app", "services", "courier_weights.npz")
np.savez_compressed(out_path, **state)
size_kb = os.path.getsize(out_path) / 1024
print(f"\nSaved to {out_path} ({size_kb:.0f} KB)")
