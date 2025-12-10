# DeepLearning Framework

A custom framework for deep learning experiments.

## Tensor Operations

We support basic tensor ops.

```python
x = Tensor([1, 2, 3])
y = x * 2
```

## Computation Graph

```mermaid
graph BT
    Input --> L1[Layer 1]
    L1 --> L2[Layer 2]
    L2 --> Output
    Output --> Loss
```
