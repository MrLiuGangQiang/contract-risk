"""内置合同风险规则库（《10-合同风险规则配置设计》，极简模型）。

- 14 个开放维度、53 条一句话规则（乙方视角：供应商/服务方审查合同）；
- 每条规则仅 `rule_text`（AI 理解并逐条校验合同的依据）+ 可选维度；
- bootstrap 按 rule_text 幂等补种，不覆盖用户修改。
"""
from typing import Any

DEFAULT_RISK_RULES: list[dict[str, Any]] = [
    # ==================== 1. 项目管理 ====================
    {"rule_text": "项目必须约定明确的里程碑、工期与延期责任，延期责任应区分甲方原因与乙方原因", "category": "project", "enabled": True, "sort_order": 10},
    {"rule_text": "需求或范围变更必须书面确认，并同步调整费用和工期", "category": "project", "enabled": True, "sort_order": 20},
    {"rule_text": "合同必须明确关键人员、资源投入和人员替换机制，人员替换应有合理程序", "category": "project", "enabled": True, "sort_order": 30},
    {"rule_text": "交付物清单、验收标准和验收流程必须完整明确", "category": "project", "enabled": True, "sort_order": 40},
    {"rule_text": "付款节点应与里程碑交付成果挂钩，甲方未按节点付款的，乙方有权暂停后续交付", "category": "project", "enabled": True, "sort_order": 50},
    {"rule_text": "合同必须约定可量化、可执行的验收标准和测试用例", "category": "project", "enabled": True, "sort_order": 60},

    # ==================== 2. 技术风险 ====================
    {"rule_text": "使用开源或第三方组件前必须评估许可证合规风险", "category": "technology", "enabled": True, "sort_order": 100},
    {"rule_text": "数据存储、传输、访问控制与个人信息保护必须符合安全要求", "category": "technology", "enabled": True, "sort_order": 110},
    {"rule_text": "系统性能指标、并发容量和压测验收标准必须明确约定", "category": "technology", "enabled": True, "sort_order": 120},
    {"rule_text": "技术栈、依赖版本和长期维护责任必须明确，维护范围与费用边界应清晰", "category": "technology", "enabled": True, "sort_order": 130},
    {"rule_text": "源码、文档与部署资产的交付或托管安排必须明确，且不得无偿转移乙方背景知识产权与通用组件", "category": "technology", "enabled": True, "sort_order": 140},
    {"rule_text": "系统间接口规范、集成责任与联调验收必须明确", "category": "technology", "enabled": True, "sort_order": 150},

    # ==================== 3. 合同条款 ====================
    {"rule_text": "付款节点、比例与付款前提条件必须明确，付款进度应与交付成果匹配，甲方逾期付款乙方有权暂停履约并计收利息", "category": "contract", "enabled": True, "sort_order": 200},
    {"rule_text": "违约情形、违约金、赔偿范围与责任上限必须约定完整", "category": "contract", "enabled": True, "sort_order": 210},
    {"rule_text": "合同主体资质、经营范围、签署人授权必须合法有效", "category": "contract", "enabled": True, "sort_order": 220},
    {"rule_text": "项目成果的知识产权归属、许可范围必须明确约定", "category": "contract", "enabled": True, "sort_order": 230},
    {"rule_text": "争议解决方式、管辖机构与适用法律必须明确", "category": "contract", "enabled": True, "sort_order": 240},

    # ==================== 4. 通用风险 ====================
    {"rule_text": "不可抗力的定义、通知义务与后果处理必须完整约定", "category": "general", "enabled": True, "sort_order": 300},
    {"rule_text": "通知方式、送达地址与联系人必须明确，保证重要文件有效送达", "category": "general", "enabled": True, "sort_order": 310},
    {"rule_text": "保密范围、保密期限与违约责任必须明确约定，且不得过度限制乙方开展同类业务", "category": "general", "enabled": True, "sort_order": 320},
    {"rule_text": "合同解除或终止的条件、程序与善后义务必须明确，甲方单方解除应有合理理由，已履约部分必须按约付款", "category": "general", "enabled": True, "sort_order": 330},

    # ==================== 5. 主体与签署 ====================
    {"rule_text": "合同相对方必须具备履行合同所需的资质、许可与经营范围", "category": "subject", "enabled": True, "sort_order": 400},
    {"rule_text": "合同签署人必须获得有效授权，盖章用印流程必须合规", "category": "subject", "enabled": True, "sort_order": 410},
    {"rule_text": "应评估甲方的资信状况、付款能力与既往付款记录", "category": "subject", "enabled": True, "sort_order": 420},

    # ==================== 6. 付款与结算 ====================
    {"rule_text": "付款节点、付款比例与付款前提条件必须一一对应明确", "category": "payment", "enabled": True, "sort_order": 500},
    {"rule_text": "甲方逾期付款的违约责任、利息与催告机制必须明确约定", "category": "payment", "enabled": True, "sort_order": 510},
    {"rule_text": "发票类型、开具时限与税率承担必须明确", "category": "payment", "enabled": True, "sort_order": 520},
    {"rule_text": "价格调整机制、费用上限与额外费用承担必须约定", "category": "payment", "enabled": True, "sort_order": 530},
    {"rule_text": "付款不得以甲方主观满意或模糊条件作为无限期付款前提", "category": "payment", "enabled": True, "sort_order": 540},

    # ==================== 7. 交付与验收 ====================
    {"rule_text": "交付时间、交付方式与迟延交付责任必须明确，迟延责任应区分甲方原因与乙方原因", "category": "delivery", "enabled": True, "sort_order": 600},
    {"rule_text": "验收标准必须可量化、可执行，并附测试用例与验收流程", "category": "delivery", "enabled": True, "sort_order": 610},
    {"rule_text": "验收期限与逾期视为验收通过/拒收机制必须约定", "category": "delivery", "enabled": True, "sort_order": 620},
    {"rule_text": "验收不通过的整改期限、复验流程与费用承担必须明确", "category": "delivery", "enabled": True, "sort_order": 630},

    # ==================== 8. 违约责任 ====================
    {"rule_text": "违约情形应逐项列明，不得使用笼统免责或单方免责条款", "category": "breach", "enabled": True, "sort_order": 700},
    {"rule_text": "违约金计算方式、损失赔偿范围与间接损失承担必须明确", "category": "breach", "enabled": True, "sort_order": 710},
    {"rule_text": "乙方赔偿责任应设总额上限并排除间接损失，不得约定无限或连带责任", "category": "breach", "enabled": True, "sort_order": 720},

    # ==================== 9. 知识产权 ====================
    {"rule_text": "项目成果的知识产权归属必须明确约定；乙方背景技术、通用组件、开源代码及既有知识产权不因本合同无偿转让或许可给甲方", "category": "ip", "enabled": True, "sort_order": 800},
    {"rule_text": "双方背景知识产权与既有技术的使用边界必须区分清楚", "category": "ip", "enabled": True, "sort_order": 810},
    {"rule_text": "第三方知识产权侵权责任与索赔承担必须明确，因甲方提供素材或指示引发的侵权由甲方承担", "category": "ip", "enabled": True, "sort_order": 820},
    {"rule_text": "成果使用许可的范围、期限与是否可转授权必须明确", "category": "ip", "enabled": True, "sort_order": 830},

    # ==================== 10. 保密与数据安全 ====================
    {"rule_text": "保密信息范围、保密期限与保密义务人必须明确", "category": "confidential", "enabled": True, "sort_order": 900},
    {"rule_text": "个人信息处理、数据出境与数据合规义务必须符合法律法规", "category": "confidential", "enabled": True, "sort_order": 910},
    {"rule_text": "数据安全措施、泄露通知与事故责任必须明确约定", "category": "confidential", "enabled": True, "sort_order": 920},

    # ==================== 11. 争议解决 ====================
    {"rule_text": "争议解决方式（诉讼/仲裁）、管辖地点与机构必须明确", "category": "dispute", "enabled": True, "sort_order": 1000},
    {"rule_text": "合同适用法律必须明确（涉外合同尤应约定准据法）", "category": "dispute", "enabled": True, "sort_order": 1010},
    {"rule_text": "维权费用（律师费、公证费等）的承担方式应当约定", "category": "dispute", "enabled": True, "sort_order": 1020},

    # ==================== 12. 税务与发票 ====================
    {"rule_text": "税费承担、含税/不含税价款与税率变化处理必须明确", "category": "tax", "enabled": True, "sort_order": 1100},
    {"rule_text": "发票开具时限、类型与未开票的违约责任必须约定", "category": "tax", "enabled": True, "sort_order": 1110},

    # ==================== 13. 质保与售后 ====================
    {"rule_text": "质保期限、起算时间与质保范围必须明确约定", "category": "warranty", "enabled": True, "sort_order": 1200},
    {"rule_text": "质保范围、响应时限与免费/收费服务边界必须明确", "category": "warranty", "enabled": True, "sort_order": 1210},
    {"rule_text": "运维服务内容、SLA 与驻场支持要求必须明确约定，驻场服务成本承担应清晰", "category": "warranty", "enabled": True, "sort_order": 1220},

    # ==================== 14. 合规审查 ====================
    {"rule_text": "合同内容不得违反法律法规、行业监管与强制性规定", "category": "compliance", "enabled": True, "sort_order": 1300},
    {"rule_text": "不得涉及出口管制、制裁名单等跨境合规风险条款", "category": "compliance", "enabled": True, "sort_order": 1310},
]
