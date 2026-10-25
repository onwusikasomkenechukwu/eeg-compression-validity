"""Device selection: cpu, cuda (NVIDIA workstation or cluster), dml (DirectML, e.g. the
Radeon iGPU on Windows), or auto (cuda if available, else cpu). Accelerators are used for
FP32 training only; quantization and scoring always run on the CPU."""
import platform

import torch


def get_device(name="cpu"):
    if name == "auto":
        name = "cuda" if torch.cuda.is_available() else "cpu"
    if name == "dml":
        import torch_directml  # Windows: pip install torch-directml (pins its own torch)
        return torch_directml.device()
    if name == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("device 'cuda' requested but torch.cuda.is_available() is False")
    return torch.device(name)


def describe(name):
    """Short record of the software and hardware a job ran on, saved with its results."""
    info = {"device": name, "torch": torch.__version__, "python": platform.python_version(),
            "platform": platform.platform(), "cpu_threads": torch.get_num_threads()}
    if name == "cuda" and torch.cuda.is_available():
        info["gpu"] = torch.cuda.get_device_name(0)
    if name == "dml":
        import torch_directml
        info["gpu"] = torch_directml.device_name(0)
    return info
