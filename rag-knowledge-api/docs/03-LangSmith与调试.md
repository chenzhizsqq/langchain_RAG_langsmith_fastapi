# LangSmith 与调试

很多人第一次做 RAG，最大的误区是只盯着最终答案。实际上，你应该盯的是“过程”。

LangSmith 的作用，就是把这个过程展开给你看。

## 怎么开启

在 `.env` 里至少设置：

```env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=你的_key
LANGSMITH_PROJECT=rag-knowledge-api
```

然后重新启动服务。

## 你应该重点看什么

### 1. ingest trace

你可以看到导入时是否真的发生了：

- 文档读取
- chunk 生成
- embedding
- 写入向量库

### 2. ask trace

这部分最有价值。你要看：

- 用户问题是什么
- 检索返回了哪些 chunk
- prompt 最终长什么样
- 模型输出了什么

## 怎么判断问题

### 检索结果不相关

优先怀疑：

- 文档内容不够
- chunk 切法不对
- top_k 太小
- embedding 模型不合适

### 检索结果明明相关，但答案还是偏

优先怀疑：

- prompt 没有限制模型
- context 太长，重点被稀释
- 模型本身输出风格太发散

## 对初学者最有帮助的习惯

每次改一个变量，就重新看 trace。

例如：

1. 把 chunk_size 从 700 改成 400
2. 再问同一个问题
3. 比较检索片段有没有变化
4. 比较最终答案有没有改善

你一旦养成这个习惯，做 AI 应用时就不会只靠猜。
