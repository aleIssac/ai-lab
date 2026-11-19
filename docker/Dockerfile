# syntax=docker/dockerfile:1
FROM codercom/code-server:latest
USER root

ARG WITH_BIGDATA=false
ARG WITH_LLM_APP=false

# 换成国内 apt 源，否则 deb.debian.org 在国内极慢（deb822 与老格式都兼容处理）
RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' \
        /etc/apt/sources.list.d/debian.sources; \
    fi; \
    if [ -f /etc/apt/sources.list ]; then \
      sed -i 's|deb.debian.org|mirrors.aliyun.com|g; s|security.debian.org|mirrors.aliyun.com|g' \
        /etc/apt/sources.list; \
    fi

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv python3-dev build-essential \
      curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip -i https://mirrors.aliyun.com/pypi/simple

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install \
      torch torchvision \
      --index-url https://download.pytorch.org/whl/cpu

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -i https://mirrors.aliyun.com/pypi/simple \
      numpy pandas scikit-learn matplotlib seaborn joblib \
      ipykernel jupyter_client \
      mlflow fastapi "uvicorn[standard]" streamlit

ENV SPARK_HOME=/opt/spark

# PySpark 在 PyPI 上只有 450MB 源码包（无 wheel），pip 安装需要现场组装，极慢。
# 改为直接取 Apache 官方二进制包（清华镜像 22MB/s），解压即用。
RUN if [ "$WITH_BIGDATA" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends openjdk-21-jre-headless && \
      rm -rf /var/lib/apt/lists/* && \
      curl -sL -o /tmp/spark.tgz \
        https://mirrors.tuna.tsinghua.edu.cn/apache/spark/spark-4.0.4/spark-4.0.4-bin-hadoop3.tgz && \
      tar -xzf /tmp/spark.tgz -C /opt && \
      mv /opt/spark-4.0.4-bin-hadoop3 /opt/spark && \
      rm -f /tmp/spark.tgz && \
      pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple py4j && \
      printf '%s\n' /opt/spark/python \
        > /opt/venv/lib/python3.13/site-packages/spark-home.pth && \
      /opt/venv/bin/python -c "import pyspark; print('PySpark', pyspark.__version__)"; \
    fi

ENV PATH=$SPARK_HOME/bin:$PATH

# RAG 用 TF-IDF 向量化（sklearn 已装），不需要向量库；这里只补一个官方 SDK
RUN if [ "$WITH_LLM_APP" = "true" ]; then \
      pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple openai; \
    fi

RUN python -m ipykernel install --name ai-lab --display-name "Python (ai-lab)"

# 预先创建运行时目录并交给 coder，否则 named volume 首次挂载时属 root，code-server 写不进去
RUN mkdir -p /home/coder/.config /home/coder/.local /home/coder/.continue \
 && chown -R coder:coder /home/coder/.config /home/coder/.local /home/coder/.continue

USER coder
WORKDIR /home/coder/project
EXPOSE 8080
