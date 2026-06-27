# Clone Store

全能型脱机后台下载工具，专为服务器 SSH 断连和国内代理网络波动设计。
支持 Hugging Face 大模型多线程断点续传和 GitHub 仓库的抗压防断连克隆。

## 核心特性
- **防断线架构 (Daemon Worker)**：哪怕立刻关闭终端或 SSH 断网，它依旧能在后台坚定执行。
- **强制防刷流量**：深度整合 Clash Verge 解析，硬编码锁死 **MUNIU 订阅**，有效拦截误用其他计费节点。
- **Hugging Face 断点续传**：支持局部文件选择和 `ALL` 全选，100% 免疫网络闪断。
- **GitHub 自动代理映射**：无论你是传入 HTTPS 还是 SSH (`git@`) 链接，脚本会自动挂载底层代理链并植入失败重试机制。

## 安装使用
1. 直接运行脚本：
   ```bash
   python3 clone_store.py
   ```
2. 输入你想克隆或下载的 GitHub 或 Hugging Face 链接。
3. 按照提示输入 Token 或者选择序号即可。

## 保存路径
- **Hugging Face**：`~/.steven/clone_store/huggingface/`
- **GitHub**：`~/.steven/clone_store/github/`

## 日志查看
后台任务一旦启动，前台秒退。可以通过提示中给出的 `tail -f` 命令随时接管查看下载进度。
