graph TD
    %% 定义样式
    classDef perception fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef decision fill:#fff9c4,stroke:#fbc02d,stroke-width:2px;
    classDef memory fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    classDef execution fill:#ffebee,stroke:#c62828,stroke-width:2px;
    classDef feedback fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef storage fill:#eceff1,stroke:#455a64,stroke-width:2px,shape:cylinder;

    %% =======================
    %% 1. 感知模块 (Perception)
    %% =======================
    subgraph Perception_Layer [👁️ 感知模块 Perception]
        direction TB
        Input_Source[多模态输入源<br/>文本/语音/图像/API事件]
        
        subgraph PreProcess [预处理工厂]
            Denoise[去噪与整理]
            Translate[多语言翻译]
        end
        
        Standardize[数据标准化<br/>Standardized JSON]
        
        Input_Source --> PreProcess
        PreProcess --> Standardize
    end
    class Perception_Layer,Input_Source,PreProcess,Denoise,Translate,Standardize perception;

    %% =======================
    %% 2. 记忆模块 (Memory)
    %% =======================
    subgraph Memory_System [🧠 记忆系统 Memory]
        direction TB
        
        subgraph Short_Term [短期/工作记忆]
            Context_Window[当前上下文]
            Session_History[会话历史]
        end
        
        subgraph Long_Term [长期记忆 (双引擎)]
            Vector_DB[("向量数据库<br/>(非结构化 RAG)")]
            Knowledge_Graph[("知识图谱<br/>(实体关系网络)")]
        end
        
        Retrieval_Engine[检索增强 RAG<br/>双路召回]
        
        Vector_DB <--> Retrieval_Engine
        Knowledge_Graph <--> Retrieval_Engine
    end
    class Memory_System,Short_Term,Context_Window,Session_History,Retrieval_Engine memory;
    class Vector_DB,Knowledge_Graph storage;

    %% =======================
    %% 3. 决策引擎 (Decision)
    %% =======================
    subgraph Decision_Engine [⚡ 决策引擎 - 大脑系统]
        direction TB
        
        Goal_Decomp[Step 1: 目标拆解]
        Plan_Gen[Step 2: 方案生成<br/>(多路径规划)]
        Evaluator[Step 3: 优劣评估<br/>(Self-Critic)]
        Final_Decision[Step 4: 决策输出]
        
        Goal_Decomp --> Plan_Gen
        Plan_Gen --> Evaluator
        Evaluator -- 驳回 --> Plan_Gen
        Evaluator -- 通过 --> Final_Decision
        
        %% 动态调整
        Dynamic_Replan{异常检测?}
        Final_Decision --> Dynamic_Replan
        Dynamic_Replan -- 是:重新规划 --> Goal_Decomp
        Dynamic_Replan -- 否:执行指令 --> Execute_Cmd
    end
    class Decision_Engine,Goal_Decomp,Plan_Gen,Evaluator,Final_Decision,Dynamic_Replan decision;

    %% =======================
    %% 4. 执行系统 (Execution)
    %% =======================
    subgraph Execution_System [🛠️ 执行系统 - 手脚系统]
        direction TB
        
        Execute_Cmd[接收指令]
        
        subgraph Safety_Layer [可靠性保障]
            Human_Check[👤 人工确认<br/>(高风险操作)]
            Snapshot[📸 状态快照]
        end
        
        subgraph Tools [工具集 Tool Schema]
            API_Call[API 调用]
            Code_Interpreter[代码解释器]
            Plugin_Action[插件操作]
        end
        
        Result_Check{执行成功?}
        Rollback[🔙 回滚操作]
        Retry[🔄 网络重试]
        
        Execute_Cmd --> Safety_Layer
        Safety_Layer --> Tools
        Tools --> Result_Check
        
        Result_Check -- 失败 --> Retry
        Retry -- 超过阈值 --> Rollback
        Result_Check -- 成功 --> Output_Result[执行结果]
    end
    class Execution_System,Execute_Cmd,Safety_Layer,Human_Check,Snapshot,Tools,API_Call,Code_Interpreter,Plugin_Action,Result_Check,Rollback,Retry,Output_Result execution;

    %% =======================
    %% 5. 反馈与进化 (Evolution)
    %% =======================
    subgraph Evolution_System [📈 反馈进化 - 自我成长]
        direction TB
        
        Reflection[Tier 1: 反思复盘<br/>(目标达成? 冗余步骤?)]
        Extract_Exp[经验提取]
        RL_Update[Tier 2: 策略权重调整<br/>(强化学习)]
        
        Output_Result --> Reflection
        Reflection --> Extract_Exp
        Extract_Exp --> RL_Update
    end
    class Evolution_System,Reflection,Extract_Exp,RL_Update feedback;

    %% =======================
    %% 全局连接 (Data Flow)
    %% =======================
    
    %% 感知 -> 记忆 & 决策
    Standardize --> Retrieval_Engine
    Standardize ==> Goal_Decomp
    
    %% 记忆 <-> 决策 (双向交互)
    Retrieval_Engine <==> Goal_Decomp
    Retrieval_Engine -.-> Evaluator
    
    %% 执行 -> 记忆 (写入历史)
    Output_Result -.-> Session_History
    
    %% 进化 -> 记忆 (知识沉淀)
    Extract_Exp ==> Vector_DB
    Extract_Exp ==> Knowledge_Graph