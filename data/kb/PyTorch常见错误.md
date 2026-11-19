# PyTorch 常见错误与排查

## 张量形状不匹配

最常见的报错是矩阵乘法维度不匹配，典型信息是 `mat1 and mat2 shapes cannot be multiplied`。

以 `x @ y` 为例，要求 x 的最后一维等于 y 的倒数第二维。如果 x 是形状 (3, 4)，y 是 (3, 5)，那么 x 的最后一维是 4，y 的倒数第二维是 3，两者不相等，无法相乘。正确的做法是把 y 转置成 (4, 5)，或者检查上游网络层的输出维度。

在卷积网络中，全连接层之前必须把特征图展平。如果卷积层输出是 (batch, 64, 7, 7)，进入全连接层前要用 `x.view(x.size(0), -1)` 变成 (batch, 3136)。忘记展平就会出现维度不匹配。

## 设备不一致

报错信息通常是 `Expected all tensors to be on the same device, but found at least two devices, cuda:0 and cpu`。

原因是模型在 GPU 上，但输入数据还在 CPU 上，或者反过来。解决方法是把数据和模型统一：模型用 `model.to(device)`，每个 batch 的数据也要 `data.to(device)`。

还有一个隐蔽的情况：在损失函数里新建的张量默认在 CPU 上。比如手动实现损失时用了 `torch.zeros(...)`，却没有指定 device，就会触发这个错误。正确写法是 `torch.zeros(..., device=x.device)`。

## 梯度爆炸与梯度消失

训练深层网络时，如果损失突然变成 NaN，通常是梯度爆炸。可以先打印梯度范数确认：遍历 `model.parameters()`，计算每个参数梯度的 norm。

应对手段有三种。梯度裁剪是最直接的，用 `torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)` 把梯度范数限制在阈值内。降低学习率也有效。改用残差连接或 BatchNorm 能从结构上缓解。

梯度消失的表现相反：损失下降极慢，浅层参数几乎不更新。常见原因是用了 Sigmoid 或 Tanh 堆了很多层，换成 ReLU 系列通常能改善。

## 显存不足

报错是 `CUDA out of memory`。先看是不是 batch size 太大，减半试试。如果减了还不行，检查是否有张量意外保留了计算图。

一个典型错误是在训练循环里把 loss 存进列表却没加 `.item()`，导致整个计算图被保留，显存持续增长。正确做法是记录 `loss.item()` 这个标量。

另外，验证阶段要用 `with torch.no_grad():` 包裹，否则会构建不必要的计算图。推理完成后，可以用 `torch.cuda.empty_cache()` 释放缓存。

## 参数更新没有生效

如果训练 loss 完全不下降，先检查是否忘记写 `optimizer.step()`。另一个常见原因是忘记 `optimizer.zero_grad()`，导致梯度在多个 batch 之间累加。

还要确认模型处于正确的模式：训练时 `model.train()`，推理时 `model.eval()`。如果忘了切 eval，Dropout 和 BatchNorm 的行为会不对，验证指标会异常偏低。
