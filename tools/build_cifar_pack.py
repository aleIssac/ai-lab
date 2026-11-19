"""把 CIFAR-10 parquet 转成 ConvNetJS demo 需要的数据包格式。

ConvNetJS 期望（见 demo/js/images-demo.js）：
    demo/cifar10/cifar10_batch_0.png .. cifar10_batch_49.png   训练集，每批 1000 样本
    demo/cifar10/cifar10_batch_50.png                           测试集，10000 样本
    demo/cifar10/cifar10_labels.js                              var labels=[...]

关键差异（比 MNIST 麻烦）：
    读取循环是 for(dc) for(xc) for(yc)，像素序号 i = xc*32 + yc，
    即按「列优先」存取。而图片像素是行优先存储的，
    所以生成时必须先把 32x32 的图转置，再按行展开。

用法：
    python tools/build_cifar_pack.py
"""

import io
import os

import numpy as np
import pyarrow.parquet as pq
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "data", "_mnist_src")
OUT_DIR = r"D:\Environment\Server\apps\convnetjs\demo\cifar10"

BATCH = 1000
DIM = 32
W = DIM * DIM


def load(path):
    table = pq.read_table(path)
    n = table.num_rows
    raws = table.column("img").to_pylist()
    labels = table.column("label").to_pylist()
    print(f"  读取 {os.path.basename(path)}: {n} 张")
    return raws, [int(v) for v in labels]


def to_canvas(raws, start, count):
    """取 [start, start+count) 区间，转置后拼成 (count, 1024, 3) 的画布。"""
    canvas = np.zeros((count, W, 3), dtype=np.uint8)
    for k in range(count):
        raw = raws[start + k]["bytes"]
        arr = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"))
        canvas[k] = arr.transpose(1, 0, 2).reshape(W, 3)
    return canvas


def save(canvas, path):
    Image.fromarray(canvas, mode="RGB").save(path, optimize=True)
    size = os.path.getsize(path) / 1024 / 1024
    print(f"  {os.path.basename(path)}  {canvas.shape[0]} 样本  {size:.1f} MB")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[1/3] 读取训练集")
    train_raws, train_labels = load(os.path.join(SRC_DIR, "cifar_train.parquet"))
    print("[2/3] 读取测试集")
    test_raws, test_labels = load(os.path.join(SRC_DIR, "cifar_test.parquet"))

    print("[3/3] 生成拼图")
    n_batch = len(train_raws) // BATCH
    for b in range(n_batch):
        canvas = to_canvas(train_raws, b * BATCH, BATCH)
        save(canvas, os.path.join(OUT_DIR, f"cifar10_batch_{b}.png"))

    save(to_canvas(test_raws, 0, len(test_raws)),
         os.path.join(OUT_DIR, f"cifar10_batch_{n_batch}.png"))

    labels = train_labels + test_labels
    label_path = os.path.join(OUT_DIR, "cifar10_labels.js")
    with open(label_path, "w", encoding="utf-8") as f:
        f.write("var labels=[" + ",".join(str(v) for v in labels) + "];")

    print(f"\n完成：{n_batch} 个训练 batch + 1 个测试 batch")
    print(f"标签文件：{label_path}（{len(labels)} 个）")


if __name__ == "__main__":
    main()
