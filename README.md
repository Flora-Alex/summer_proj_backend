## 关于[open-webui](https://github.com/open-webui/open-webui)
open-webui是一个非常好的大模型聊天集成软件，他提供的[pipelines](https://github.com/open-webui/pipelines)的方式，极大便利了集成其它大模型工具API到它的对话中来。
## 关于[ragflow](https://github.com/infiniflow/ragflow)
ragflow是一个比较好用的大模型知识库开源项目
## 使用方法
- 首先下载open-webui的[pipelines](https://github.com/open-webui/pipelines)项目
- 启动这个项目后，参考[pipelines](https://github.com/open-webui/pipelines)的README，在open-webui中的配置好pipelines的链接
- 配置好链接后，将本项目的open-webui-pipeline-for-ragflow.py在open-webui中上传后，配置以下四个参数：
  - API_KEY: ragflow的apikey
  - AGENT_ID: ragflow的agentid
  - HOST: ragflow的host, host要以http://或https://开头.
  - PORT: ragflow的port
- 然后你就可以实现在open-webui中调用ragflow中的agent，并且拥有美观的交互界面了。