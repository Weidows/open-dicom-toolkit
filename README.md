## 一、目标（Problem / Vision）

构建一套可被 AI Agent（如基于 LLM 的 planner/agent）自主调用的 DICOM 分析工具链，使得：

- AI 可以像调用"技能（skill）/算子（operator）"一样，选择、组合、执行检测/分割/测量/统计等任务；
- 算子以插件形式可替换（模型或算法替换不影响整体架构）；
- 支持流程化、图式工作流编排（node/edge），便于复用与审计；
- 面向超声场景：支持 2D 单帧、短 cine 序列，保留测量语义与物理尺度（像素间距、深度等）。

## 二、设计原则

- 可编排（Composable）：每个步骤是独立可替换的算子（Operator/Plugin）。
- 可被 AI 协同编排（AI-first）：提供技能元数据与能力描述，方便 LLM 做能力匹配与计划。
- 数据可追溯（Provenance）：输入/输出/版本/参数均记录，便于审计与再现。
- 最小侵入、Python 优先：以 Python 为主，兼容 MONAI / ONNX / TorchScript / OpenCV / SimpleITK。
- DICOM 兼容：保留并使用 DICOM 元数据（PixelSpacing、ImageOrientation、ImagePosition、FrameOfReference、SOPInstanceUID 等）。

## 三、整体架构（高层）

- Agent Core（Planner + Executor）
  - LLM Planner：把用户指令转成工作流计划（节点链）。
  - Workflow Executor：解析并执行节点、管理并发/错误回滚。
- Plugin Manager / Registry
  - 插件目录与元数据（capabilities、input/output schema、version、resource-requirements）。
  - 支持两种插件运行方式：内嵌 Python class（entrypoint）或容器化服务（REST/gRPC）。
- Operator（算子）
  - 读取器（DICOM Reader）、预处理、推理（ModelOperator）、后处理、测量、报告生成（DICOM SR/JSON）。
- Artifact Store / Data Lake
  - 原始 DICOM 存储（可接 Orthanc/DICOMweb）与中间产物（NIfTI/PNG/JSON）。
- Model Manager
  - 模型注册、版本、导出（TorchScript/ONNX）、加速器适配（TensorRT/ORT）。
- UI / CLI / API
  - 用于上传 DICOM、查看工作流、审阅结果与手动触发。
- Observability & Security
  - 日志、指标、审计日志、鉴权（OAuth/LDAP）、隐私保护与合规支持。

（注：生产场景可在上述基础上替换 Operator 为 MONAI Deploy 容器/Clara Deploy）

## 四、数据流与工作流示例

1. 数据接入：Agent 从本地文件夹/Orthanc/DICOMweb 发现 DICOM 数据，并读取相关辅助文件（Excel/Word）。
2. 元数据提取：解析 Patient/Study/Series，提取 PixelSpacing、ImageOrientation 等。
3. 预处理：去噪、归一化、resize、帧抽样（cine）。
4. 推理：选择合适模型（分割/检测），返回概率图或 bbox。
5. 后处理：连通域、形态学、置信度过滤、时间聚合（cine）。
6. 测量：基于物理尺度计算面积、直径、体积估算、心率/血流等。
7. 报告：生成 DICOM SR、JSON 报表，上传/回写到 PACS（Orthanc）。
8. 审阅/回环：若需要人工修正，支持 MONAI Label/ OHIF 等前端交互，再入训练集。

示例工作流（YAML）：

```yaml
workflow:
  name: us_exam_analysis
  nodes:
    - id: read
      type: DICOMReader
      params: {path: "/data/exam_123"}
    - id: meta
      type: DICOMMetaExtractor
      inputs: [read]
    - id: preprocess
      type: USPreprocess
      inputs: [read, meta]
    - id: model_seg
      type: ModelOperator
      model: "us_seg_v1"
      inputs: [preprocess]
    - id: post
      type: Postprocess
      inputs: [model_seg]
    - id: measure
      type: MeasurementOperator
      inputs: [post, meta]
    - id: report
      type: ReportGenerator
      inputs: [measure, meta]
  edges:
    - [read, meta]
    - [meta, preprocess]
    - [preprocess, model_seg]
    - [model_seg, post]
    - [post, measure]
    - [measure, report]
```

## 五、Plugin / Operator 规范（Python 风格）

- 每个插件需实现元数据（name, version, capabilities, input_schema, output_schema），并提供标准的 `run(context: dict) -> dict` 接口。
- 支持同步/异步执行。容器化插件需通过健康检查与 capability 描述注册到 Registry。

示例抽象基类：

```python
class OperatorBase:
    name: str
    version: str
    capabilities: List[str]  # e.g. ["segmentation", "measurement"]
    input_schema: dict
    output_schema: dict

    def __init__(self, config: dict):
        ...

    def run(self, ctx: dict) -> dict:
        """接收并返回 ctx（包含artifact引用等）"""
        raise NotImplementedError
```

推荐插件打包方式

- Python plugin： setuptools entrypoint（例如 group: dicom_platform.plugins）。
- Container plugin：遵循 REST/gRPC 接口并在 Registry 提交 capability manifest（包含 resource: gpu/cpu, env）。

## 六、Agent 与 Skill（技能）集成（LLM 驱动）

- 每个 plugin 在 Registry 中提供自然语言描述 + capability tags（e.g., "US segmentation", "measure longest diameter (mm)").
- LLM Planner 接收用户高层指令（例："请在此病例中找到并测量肿块最大径"），然后：
  1. 根据 capability 匹配合适插件；
  2. 生成 DAG（节点与参数）并请求 Executor 执行；
  3. 在执行过程中可以做工具调用链（调用预处理->推理->测量->报告）并以自然语言/结构化结果回报用户。
- 安全：LLM 的任意决策必须记录并可回溯；关键测量建议人审阅（human-in-the-loop）。

## 七、超声 / DICOM 特殊注意点（关键）

- Pixel spacing: 对测量至关重要（检查 (PixelSpacing) 或 (ImagerPixelSpacing)），对于非标注 probe/角度需校正。
- Frame-based cine: 有时间维度的聚合策略（平均/最大/连续帧追踪）。
- Depth/Scale：有些设备像素不是等距，使用 ImagePosition/Orientation 与 PatientCoordinate 系统转换。
- 声学阴影、探头角度与增益会影响模型泛化，应记录设备型号并在插件元数据中标注训练集来源。
- 对隐私：敏感字段须脱敏或通过访问控制限制。

## 八、部署与运维建议

- 本地开发：Python 模式（entrypoint plugin）+ Docker 测试环境。
- 生产部署：containerized plugins + Kubernetes + GPU nodepool；使用 message queue（RabbitMQ/Redis）做任务调度。
- DICOM 存取：Orthanc 作 PACS / DICOMweb 适配层；插件通过 DICOMweb 上传/拉取。
- 监控：Prometheus + Grafana；审计日志写入 ELK。

## 九、测试、CI、验证

- 单元测试每个 Operator（输入/输出契约）；集成测试用小规模 DICOM 例子（包括 edge case: no target, multi-target）。
- 性能测试：延迟与吞吐（frames/s），内存与GPU利用。
- 临床验证流程：与放射/超声专家协同，记录读数差异与一致性（Bland-Altman/ICC 分析）。

## 十、合规与安全

- 数据加密（静态/传输），访问控制审计。
- 保留可追溯的版本标记（模型 hash, plugin version, workflow config）。
- 若用于临床诊断，遵循本地法规（FDA/CE 等）与临床试验流程。

---

## 典型使用场景

### 场景：AI 自主分析一次 CT 扫查

**输入**：一个目录，包含原始 DICOM 文件夹 + `patient_info.xlsx`

**AI 自主执行过程**（无需人工干预）：

```
1. discover_files("/data/case_001/")
→ 发现 312 个 .dcm 文件 + 1 个 patient_info.xlsx

2. parse_patient_record("patient_info.xlsx")
→ 患者：男，62岁，吸烟史，主诉：咳嗽

3. parse_dicom_header(sample_dcm)
→ Modality: CT, Body Part: CHEST, Series: 2 个（平扫+增强）

4. list_plugins(category="detection", modality="CT")
→ 可用：yolo_v8_lung (v1.2.0), lung_rads_detector (v2.0.1)

5. [AI 推理] 患者有吸烟史 + 胸部 CT → 优先跑肺结节检测
   run_plugin("detection.yolo_v8_lung", {series: 平扫系列})
→ 发现 3 处可疑结节，置信度 0.87/0.73/0.62

6. run_plugin("segmentation.sam2", {bboxes: 上步输出})
→ 3 个精确 mask

7. run_plugin("measurement.volume_mm3", {masks: 上步输出})
→ 体积：127mm³ / 43mm³ / 18mm³

8. run_plugin("qualitative.image_quality", {series: 增强系列})
→ 图像质量：良好，对比剂摄取正常

9. save_report({detections, measurements, patient_info}, format="pdf")
→ 结构化报告保存至 /data/case_001/report.pdf

10. [AI 反思] 最大结节 127mm³ (≈6.3mm 等效直径)，建议随访，
    LungRADS 分类 3 类，生成最终结论文本
```