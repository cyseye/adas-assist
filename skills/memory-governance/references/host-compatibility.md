# Codex 记忆文件边界

治理对象是本仓 memory/ 或用户显式提供的目录，不读取平台隐藏记忆或宿主全局目录。memory/MEMORY.md 仅保留标题、相对路径和检索词，正文唯一保存在本仓 memory/；决策正文与索引仍归 decisions/。

`scan-memory.py` 必须指定 `--memory-root`。`recall-replay.py` 必须同时指定 `--memory-root` 和 `--data-root`；缺参拒绝，不提供宿主兼容回退。解析与分词复用本目录 scripts/recall_core.py，无自动注入或调用事件。

回放只读显式数据根内 `.adas-assist/.build/reflex-hooks.jsonl` 的已有探针，报告写该目录；该文件名只是可选历史探针格式，不表示已接入 hooks。缺日志为 no_data，命中率为 null。路径越界、索引软链接与报告越界拒绝。

同输入、同实现与同判据的前后结果才可比较；结构对账和合成探针不能证明语义正确、生产命中率或独立评审。
