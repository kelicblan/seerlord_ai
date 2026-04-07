import uuid
import os
import re
from pathlib import Path
from typing import Any
from langgraph.graph import StateGraph, END
from loguru import logger

from .state import (
    FrontendProjectCreateState,
    ModulePlan,
)
from .analyzers import DocumentAnalyzer
from .planners import ProjectPlanner
from .generators.integration import GenerationPipeline
from .memory import ShortTermMemory, LongTermMemory
from .generators.base import GenerationContext
from server.kernel.master_graph import generate_intent_title_node


def create_graph():
    """创建 frontend_project_create 的 LangGraph 工作流。"""
    workflow = StateGraph(FrontendProjectCreateState)
    
    workflow.add_node("generate_intent_title", generate_intent_title_node)
    workflow.add_node("load_memory", load_memory_node)
    workflow.add_node("analyze_document", analyze_document_node)
    workflow.add_node("plan_modules", plan_modules_node)
    workflow.add_node("generate_infrastructure", generate_infrastructure_node)
    workflow.add_node("generate_modules", generate_modules_node)
    workflow.add_node("verify_project", verify_project_node)
    workflow.add_node("save_and_deploy", save_and_deploy_node)
    workflow.add_node("save_memory", save_memory_node)
    workflow.add_node("return_result", return_result_node)
    
    workflow.set_entry_point("generate_intent_title")
    workflow.add_edge("generate_intent_title", "load_memory")
    
    workflow.add_edge("load_memory", "analyze_document")
    workflow.add_edge("analyze_document", "plan_modules")
    workflow.add_edge("plan_modules", "generate_infrastructure")
    workflow.add_edge("generate_infrastructure", "generate_modules")
    workflow.add_edge("generate_modules", "verify_project")
    workflow.add_edge("verify_project", "save_and_deploy")
    workflow.add_edge("save_and_deploy", "save_memory")
    workflow.add_edge("save_memory", "return_result")
    workflow.add_edge("return_result", END)
    
    return workflow.compile()


def load_memory_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """初始化本次会话所需的短期与长期记忆上下文。"""
    logger.info("Loading memory...")

    if not state.get("document_content"):
        next_instruction = state.get("next_instruction", "")
        if next_instruction and len(next_instruction) > 20:
            state["document_content"] = next_instruction
            state["input_content"] = next_instruction
            logger.info("Using next_instruction as document content ({} chars)", len(next_instruction))

        if not state.get("document_content"):
            messages = state.get("messages", [])
            for msg in reversed(messages):
                content = getattr(msg, "content", "") or ""
                if content and len(content) > 50:
                    state["document_content"] = content
                    state["input_content"] = content
                    logger.info("Extracted document content from messages ({} chars)", len(content))
                    break

    execution_id = state.get("execution_id")
    tenant_id = state.get("tenant_id", "default")
    user_id = state.get("user_id", "default")

    if execution_id:
        short_term = ShortTermMemory.load(execution_id)
        if short_term:
            logger.info("Restored session from memory: {}", execution_id)
        else:
            short_term = ShortTermMemory(
                session_id=execution_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )
    else:
        execution_id = str(uuid.uuid4())
        short_term = ShortTermMemory(
            session_id=execution_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )

    long_term = LongTermMemory()

    state["execution_id"] = execution_id
    state["memory_context"] = short_term.get_context_for_llm()

    return state


def analyze_document_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """解析输入文档，抽取技术栈、覆盖矩阵与摘要。"""
    logger.info("Analyzing document...")
    
    doc_content = state.get("document_content", "")
    
    if not doc_content:
        state["error_message"] = "Document content is empty"
        return state
    
    analyzer = DocumentAnalyzer(doc_content)
    
    tech_stack = analyzer.extract_tech_stack()
    coverage_matrix = analyzer.parse_coverage_matrix()
    document_summary = analyzer.generate_summary()
    
    state["tech_stack"] = tech_stack
    state["coverage_matrix"] = coverage_matrix
    state["document_summary"] = document_summary
    
    logger.info(f"Document analyzed: {document_summary.requirements_count} requirements, "
                f"{document_summary.pages_count} pages, {document_summary.routes_count} routes")
    
    return state


def plan_modules_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """根据覆盖矩阵生成模块计划与复杂度评估。"""
    logger.info("Planning modules...")
    
    coverage_matrix = state.get("coverage_matrix")
    if not coverage_matrix:
        state["error_message"] = "Coverage matrix not found"
        return state
    
    planner = ProjectPlanner(coverage_matrix)
    planner.analyze_dependencies()
    module_plans = planner.generate_module_plan()
    complexity = planner.estimate_complexity()
    
    state["module_plans"] = [p.model_dump() for p in module_plans]
    state["total_modules"] = len(module_plans)
    
    logger.info(f"Module plan created: {len(module_plans)} modules, complexity: {complexity}")
    
    return state


async def generate_infrastructure_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """复制基础模板并准备项目目录。"""
    logger.info("Generating infrastructure...")

    tech_stack = state.get("tech_stack")
    coverage_matrix = state.get("coverage_matrix")

    if not tech_stack or not coverage_matrix:
        state["error_message"] = "Missing tech_stack or coverage_matrix"
        return state

    project_id = state.get("execution_id") or str(uuid.uuid4())
    project_path = str(Path("server/data/frontend_project_runs") / project_id)
    context = GenerationContext(
        project_path=project_path,
        tech_stack=tech_stack,
        coverage_matrix=coverage_matrix,
    )

    session = ShortTermMemory(
        session_id=project_id,
        tenant_id=state.get("tenant_id", "default"),
        user_id=state.get("user_id", "default"),
    )
    session.tech_stack = tech_stack
    session.coverage_matrix = coverage_matrix
    session.document_summary = state.get("document_summary")
    pipeline = GenerationPipeline(project_path)

    try:
        result = await pipeline.infrastructure_generator.generate(session, context)
        if result.success:
            state["project_path"] = project_path
            state["generated_artifacts"] = [
                {"path": path, "content": content}
                for path, content in result.files_content.items()
            ]
            state["status"] = "infrastructure_created"
            logger.info("Infrastructure generated at {}", project_path)
        else:
            state["error_message"] = result.error
            state["status"] = "infrastructure_failed"
    except Exception as exc:
        logger.exception("Failed to generate infrastructure")
        state["error_message"] = str(exc)
        state["status"] = "infrastructure_failed"

    return state


async def generate_modules_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """执行完整流水线生成业务代码。"""
    logger.info("Generating modules...")

    tech_stack = state.get("tech_stack")
    coverage_matrix = state.get("coverage_matrix")
    project_path = state.get("project_path")

    if not all([tech_stack, coverage_matrix, project_path]):
        state["error_message"] = "Missing required state for module generation"
        return state

    context = GenerationContext(
        project_path=project_path,
        tech_stack=tech_stack,
        coverage_matrix=coverage_matrix,
    )
    session = ShortTermMemory(
        session_id=state.get("execution_id") or str(uuid.uuid4()),
        tenant_id=state.get("tenant_id", "default"),
        user_id=state.get("user_id", "default"),
    )
    session.tech_stack = tech_stack
    session.coverage_matrix = coverage_matrix
    session.document_summary = state.get("document_summary")
    if state.get("module_plans"):
        session.module_plan = [
            plan if isinstance(plan, ModulePlan) else ModulePlan(**plan)
            for plan in state["module_plans"]
        ]

    pipeline = GenerationPipeline(project_path)

    try:
        result = await pipeline.run(session, context)
        if result.success:
            state["status"] = "modules_generated"
            state["output_artifacts"] = [{"path": f} for f in result.files_generated]
            logger.info("Modules generated: {} files", len(result.files_generated))
        else:
            state["error_message"] = result.error
            state["status"] = "modules_failed"
    except Exception as exc:
        logger.exception("Failed to generate modules")
        state["error_message"] = str(exc)
        state["status"] = "modules_failed"

    return state


def verify_project_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """使用 ProjectVerifier 对生成结果进行完整项目级验证。"""
    logger.info("Verifying project...")
    
    project_path = state.get("project_path")
    
    if not project_path:
        state["error_message"] = "Project path not found"
        return state
    
    from pathlib import Path
    
    project_dir = Path(project_path)
    if not project_dir.exists():
        state["error_message"] = "Project directory not found"
        return state
    
    from .verifiers.project import ProjectVerifier
    
    verifier = ProjectVerifier(
        project_path=str(project_path),
        tech_stack=state.get("tech_stack"),
        coverage_matrix=state.get("coverage_matrix"),
    )
    result = verifier.verify()
    
    if result.passed:
        state["status"] = "verification_passed"
        logger.info("Project verification passed (score: {})", result.score)
    else:
        state["error_message"] = "; ".join(result.errors[:3])
        state["status"] = "verification_failed"
        logger.warning("Project verification failed: {} errors", len(result.errors))
    
    state["verification_score"] = result.score
    state["verification_errors"] = result.errors
    state["verification_warnings"] = result.warnings
    
    return state


async def save_and_deploy_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """
    安装依赖、构建项目、自动修复构建错误、打包 ZIP、上传 S3、部署 Vercel，并保存 Artifact。
    
    核心逻辑：智能迭代修复机制
    - 最多循环 20 次（优化后上限）
    - 提前退出条件：连续 3 轮无新修复、连续 3 轮错误数不减少
    - 每次失败后分析错误类型，调用对应的修复逻辑
    - 批量 LLM 修复减少调用次数
    - 修复历史追踪避免重复修复
    """
    import uuid, re, os, asyncio
    from pathlib import Path
    
    logger.info("Starting save and deploy with smart iteration (max 20 rounds)...")

    project_path = state.get("project_path")
    if not project_path:
        state["vercel_url"] = ""
        state["download_url"] = ""
        state["status"] = "no_project_path"
        return state

    session_id = state.get("execution_id") or str(uuid.uuid4())[:8]
    tenant_id = state.get("tenant_id")
    user_id = state.get("user_id", "default")
    max_iterations = 20
    min_iterations = 3
    
    # 提前退出条件
    consecutive_no_fix = 0
    consecutive_no_progress = 0
    previous_error_count = float('inf')
    
    # 修复历史
    fix_history = {"fixed_files": {}, "content_hashes": {}}

    import importlib.util
    executor_spec = importlib.util.spec_from_file_location(
        "executor", "server/action_skills/generate-frontend-project/executor.py"
    )
    executor_mod = importlib.util.module_from_spec(executor_spec)
    assert executor_spec and executor_spec.loader
    executor_spec.loader.exec_module(executor_mod)

    executor = executor_mod.FrontendProjectExecutor(
        project_path=project_path,
        document_content="",
        project_name="generated-project",
    )

    install_ok, install_msg = await executor.install_dependencies()
    logger.info("npm install: {} - {}", install_ok, install_msg)

    if not install_ok:
        state["status"] = "install_failed"
        state["install_ok"] = False
        state["build_ok"] = False
        state["vercel_url"] = ""
        state["download_url"] = ""
        return state

    state["install_ok"] = True

    tech_stack = state.get("tech_stack")
    coverage_matrix = state.get("coverage_matrix")
    
    all_errors = []
    all_warnings = []
    
    build_ok = False
    lint_ok = False
    lint_msg = ""
    dev_ok = False
    dev_msg = ""
    
    for iteration in range(1, max_iterations + 1):
        logger.info("=" * 60)
        logger.info(f"迭代轮次 {iteration}/{max_iterations}")
        logger.info("=" * 60)
        
        round_fixed = []
        this_round_errors = 0
        
        # 第一步：快速 TypeScript 检查
        tsc_ok, tsc_msg = await _quick_type_check(project_path)
        if tsc_ok:
            logger.info(f"[迭代 {iteration}] TypeScript 快速检查通过")
        else:
            logger.warning(f"[迭代 {iteration}] TypeScript 快速检查: {tsc_msg[:300]}")
            this_round_errors = len(re.findall(r"error TS\d+:", tsc_msg))
        
        # 如果快速检查失败，先尝试修复再全量 build
        if not tsc_ok:
            fixed_files = await _fix_build_errors(
                project_path, tsc_msg, tech_stack, coverage_matrix, fix_history
            )
            round_fixed.extend(fixed_files)
            
            if fixed_files:
                logger.info(f"[迭代 {iteration}] 批量修复了 {len(fixed_files)} 个文件")
                consecutive_no_fix = 0
            else:
                consecutive_no_fix += 1
                logger.warning(f"[迭代 {iteration}] 无法自动修复 ({consecutive_no_fix}/3 连续)")
        
        # 检查提前退出条件
        if iteration >= min_iterations:
            # 连续 3 轮无新修复
            if consecutive_no_fix >= 3:
                logger.warning(f"提前退出：连续 {consecutive_no_fix} 轮无新修复")
                break
            
            # 连续 3 轮错误数不减少
            if this_round_errors > 0 and this_round_errors >= previous_error_count:
                consecutive_no_progress += 1
                if consecutive_no_progress >= 3:
                    logger.warning(f"提前退出：连续 {consecutive_no_progress} 轮错误数未减少")
                    break
            else:
                consecutive_no_progress = 0
            
            previous_error_count = min(previous_error_count, this_round_errors)
        
        # 全量构建
        build_ok, build_msg = await executor.build_project()
        if build_ok:
            logger.info(f"[迭代 {iteration}] Build 成功!")
        else:
            logger.warning(f"[迭代 {iteration}] Build 失败: {build_msg[:500]}")
            all_errors.append(build_msg)
            
            fixed_files = await _fix_build_errors(
                project_path, build_msg, tech_stack, coverage_matrix, fix_history
            )
            round_fixed.extend(fixed_files)
            
            if fixed_files:
                consecutive_no_fix = 0
            else:
                consecutive_no_fix += 1
                logger.warning(f"[迭代 {iteration}] 无法自动修复 ({consecutive_no_fix}/3 连续)")
            
            if iteration < max_iterations:
                await asyncio.sleep(0.5)
                continue
            else:
                logger.error(f"达到最大迭代次数 {max_iterations}，仍有错误")
                break
        
        lint_ok = False
        lint_msg = ""
        lint_ok, lint_msg = await executor.lint_project()
        logger.info(f"npm run lint: {lint_ok}")
        if not lint_ok:
            logger.warning(f"[迭代 {iteration}] Lint 失败: {lint_msg[:300]}")
            all_errors.append(lint_msg)
            fixed = await _fix_lint_errors(project_path, lint_msg)
            round_fixed.extend(fixed)
            
            if iteration < max_iterations:
                await asyncio.sleep(0.5)
                continue
            else:
                logger.error(f"达到最大迭代次数 {max_iterations}，lint 错误未解决")
                break
        
        dev_ok = False
        dev_msg = ""
        if build_ok and lint_ok:
            dev_ok, dev_msg = await executor.test_dev_server()
            logger.info(f"npm run dev: {dev_ok}")
            if not dev_ok:
                logger.warning(f"[迭代 {iteration}] Dev server 失败: {dev_msg}")
                all_errors.append(dev_msg)
                
                if iteration < max_iterations:
                    await asyncio.sleep(0.5)
                    continue
                else:
                    logger.error(f"达到最大迭代次数 {max_iterations}，dev 错误未解决")
                    break
        
        if build_ok and lint_ok and dev_ok:
            logger.info("=" * 60)
            logger.info(f"🎉 所有验证通过! (迭代 {iteration} 轮)")
            logger.info("=" * 60)
            break
    
    state["build_msg"] = all_errors[-1] if all_errors else ""
    state["all_errors"] = all_errors
    state["all_warnings"] = all_warnings

    if not build_ok:
        state["status"] = "build_failed"
        state["vercel_url"] = ""
        state["download_url"] = ""
        state["build_ok"] = False
        state["lint_ok"] = lint_ok
        state["lint_msg"] = lint_msg
        state["dev_ok"] = dev_ok
        state["dev_msg"] = dev_msg
        return state

    vercel_url = ""
    vercel_url = await executor_mod.deploy_to_vercel(project_path, session_id)
    logger.info("Vercel deployment: {}", vercel_url if vercel_url else "FAILED")

    try:
        zip_data = await executor_mod.package_project(project_path)
        s3_path = f"frontend_projects/{user_id}/frontend_project_{session_id}.zip"
        download_url = await executor_mod.upload_to_s3(zip_data, s3_path)
        logger.info("ZIP uploaded: {}", download_url)

        if tenant_id and download_url:
            try:
                from server.core.database import SessionLocal
                from server.models.artifact import AgentArtifact

                intent_title = state.get("intent_title", "前端项目生成")
                async with SessionLocal() as db:
                    db.add(AgentArtifact(
                        id=str(uuid.uuid4()),
                        tenant_id=tenant_id,
                        user_id=user_id,
                        agent_id="frontend-project-create",
                        type="file",
                        value=download_url,
                        title=f"{intent_title} - 项目代码 (ZIP)",
                        description=f"生成的前端项目，会话ID: {session_id}",
                        total_tokens=0,
                    ))
                    if vercel_url:
                        db.add(AgentArtifact(
                            id=str(uuid.uuid4()),
                            tenant_id=tenant_id,
                            user_id=user_id,
                            agent_id="frontend-project-create",
                            type="url",
                            value=vercel_url,
                            title=f"{intent_title} - 在线预览 (Vercel)",
                            description=f"前端项目自动部署预览链接，会话ID: {session_id}",
                            total_tokens=0,
                        ))
                    await db.commit()
                    logger.info("Artifacts saved to database")
            except Exception as e:
                logger.warning("Failed to save artifact to DB: {}", e)
    except Exception as e:
        logger.error("ZIP/S3 save failed: {}", e)
        download_url = ""

    state["vercel_url"] = vercel_url
    state["download_url"] = download_url
    state["build_ok"] = build_ok
    state["lint_ok"] = lint_ok
    state["lint_msg"] = lint_msg
    state["dev_ok"] = dev_ok
    state["dev_msg"] = dev_msg
    state["status"] = "all_passed" if (build_ok and vercel_url) else "deployed_no_frontend_error"

    return state


async def _fix_build_errors(
    project_path: str, 
    error_msg: str, 
    tech_stack: Any, 
    coverage_matrix: Any,
    fix_history: dict = None
) -> list:
    """
    修复构建错误，返回已修复的文件列表。
    支持：
    1. 缺失的 Vue/TS 文件生成
    2. 标识符连字符命名问题修复（如 rate-limit -> rateLimit）
    3. 批量 LLM 修复（减少 LLM 调用次数）
    """
    import re
    from pathlib import Path
    
    fixed = []
    project_path = Path(project_path)
    fix_history = fix_history or {"fixed_files": {}, "content_hashes": {}}
    
    # 优先处理 TS1005 等语法错误（通常是连字符命名问题）
    if "TS1005" in error_msg or "TS1128" in error_msg or "TS1434" in error_msg:
        logger.info("检测到 TypeScript 语法错误，尝试修复连字符命名问题...")
        hyphen_fixed = await _fix_hyphen_identifiers(project_path)
        if hyphen_fixed:
            logger.info(f"✅ 已自动修复 {len(hyphen_fixed)} 个文件的连字符命名问题")
            fixed.extend(hyphen_fixed)
            logger.info(f"已修复连字符问题，共 {len(fixed)} 个文件")
    
    # 提取所有报错的文件路径
    error_file_pattern = r"(src/[^\s(]+)\((\d+),\d+\): error"
    error_files = set()
    for match in re.finditer(error_file_pattern, error_msg):
        file_path = match.group(1)
        if file_path.endswith((".ts", ".vue", ".tsx", ".jsx")):
            error_files.add(file_path)
    
    # 过滤掉已经修复过且内容未变化的文件
    files_to_fix = []
    for rel_path in error_files:
        full_path = project_path / rel_path
        if not full_path.exists():
            logger.warning(f"文件不存在: {rel_path}")
            continue
        
        # 检查是否已修复且内容未变化
        if rel_path in fix_history["fixed_files"]:
            try:
                current_content = full_path.read_text(encoding="utf-8")
                current_hash = hash(current_content)
                if current_hash == fix_history["content_hashes"].get(rel_path):
                    logger.info(f"跳过已修复且内容未变化的文件: {rel_path}")
                    continue
            except Exception:
                pass
        
        files_to_fix.append((rel_path, full_path))
    
    # 批量 LLM 修复：一次调用修复多个文件
    if files_to_fix:
        batch_fixed = await _fix_files_batch_by_llm(
            files_to_fix, 
            error_msg, 
            project_path,
            fix_history
        )
        fixed.extend(batch_fixed)
    
    vue_patterns = [
        r"Could not load (/src/views/[^\s]+\.vue)",
        r"Could not load (/@/views/[^\s]+\.vue)",
    ]
    
    missing_vue_files = []
    for pattern in vue_patterns:
        found = re.findall(pattern, error_msg)
        missing_vue_files.extend(found)
    
    if missing_vue_files:
        logger.info(f"检测到缺失 Vue 文件: {missing_vue_files}")
        for missing in missing_vue_files:
            rel_path = missing.lstrip("/")
            if not rel_path.startswith("src/"):
                rel_path = rel_path.replace("views/", "src/views/")
            
            full_path = project_path / rel_path
            if full_path.exists():
                logger.info(f"文件已存在: {full_path}")
                continue
            
            logger.info(f"正在生成缺失页面: {rel_path}")
            generated = await _generate_stub_view(
                project_path, 
                rel_path
            )
            if generated:
                fixed.append(rel_path)
                logger.info(f"✅ 已生成: {rel_path}")
    
    ts_patterns = [
        r"Could not load (/src/[^\s]+\.ts)",
        r"Could not load (/@/[^\s]+\.ts)",
    ]
    missing_ts_files = []
    for pattern in ts_patterns:
        found = re.findall(pattern, error_msg)
        missing_ts_files.extend(found)
    
    for missing in missing_ts_files:
        rel_path = missing.lstrip("/")
        if not rel_path.startswith("src/"):
            rel_path = "src/" + rel_path.replace("@/", "")
        
        full_path = project_path / rel_path
        if full_path.exists():
            continue
        
        logger.info(f"正在生成缺失 TS 文件: {rel_path}")
        os.makedirs(full_path.parent, exist_ok=True)
        name = full_path.stem.replace("-", "").replace("_", "")
        content = f"export interface {name} {{}}\n"
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        fixed.append(rel_path)
        logger.info(f"✅ 已生成 TS: {rel_path}")
    
    return fixed


async def _quick_type_check(project_path: Path) -> tuple:
    """
    快速 TypeScript 类型检查，不执行完整 build。
    使用 npx tsc --noEmit --skipLibCheck 快速验证。
    返回 (是否通过, 错误信息)。
    """
    import subprocess
    import asyncio
    
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit", "--skipLibCheck"],
            cwd=str(project_path),
            capture_output=True,
            text=True,
            timeout=60  # 60 秒超时
        )
        
        if result.returncode == 0:
            return (True, "")
        else:
            return (False, result.stdout + result.stderr)
    except subprocess.TimeoutExpired:
        return (False, "TypeScript 检查超时 (60秒)")
    except Exception as e:
        return (False, f"TypeScript 检查失败: {e}")


async def _fix_files_batch_by_llm(
    files_to_fix: list,
    error_msg: str,
    project_path: Path,
    fix_history: dict
) -> list:
    """
    批量修复多个文件，减少 LLM 调用次数。
    收集所有错误文件，一次 LLM 调用返回所有修复。
    """
    import re
    from pathlib import Path
    
    if not files_to_fix:
        return []
    
    fixed = []
    batch_size = 10  # 每次最多处理 10 个文件
    
    # 分批处理
    for i in range(0, len(files_to_fix), batch_size):
        batch = files_to_fix[i:i + batch_size]
        
        # 构建批量修复提示
        files_content = []
        for rel_path, full_path in batch:
            try:
                content = full_path.read_text(encoding="utf-8")
                file_ext = full_path.suffix
                files_content.append({
                    "path": rel_path,
                    "ext": file_ext,
                    "content": content
                })
            except Exception as e:
                logger.warning(f"无法读取文件 {rel_path}: {e}")
        
        if not files_content:
            continue
        
        # 构建批量修复 prompt
        files_section = []
        for idx, fc in enumerate(files_content):
            lang = "vue" if fc["ext"] == ".vue" else "typescript"
            files_section.append(
                f"## 文件 {idx + 1}: {fc['path']}\n"
                f"```{lang}\n"
                f"{fc['content']}\n"
                f"```"
            )
        
        prompt = f"""请批量修复以下 TypeScript/Vue 文件中的构建错误。

## 构建错误信息
```
{error_msg[:3000]}
```

## 需要修复的文件
{chr(10).join(files_section)}

请为每个文件输出修复后的完整代码，格式如下：
<file path="src/xxx.vue">
```vue
// 修复后的 Vue 代码
```
</file>

或者对于 TypeScript 文件：
<file path="src/xxx.ts">
```typescript
// 修复后的 TypeScript 代码
```
</file>

要求：
1. 保持原有业务逻辑不变
2. 修复所有类型错误和语法错误
3. 移除所有连字符（使用驼峰命名）
4. 只输出代码，不要解释

只输出 <file> 标签，不要输出任何其他内容。"""
        
        logger.info(f"批量调用 LLM 修复 {len(files_content)} 个文件 (批次 {i // batch_size + 1})")
        
        try:
            from server.core.llm import get_llm
            from langchain_core.messages import HumanMessage
            
            llm = get_llm(temperature=0.1)
            messages = [HumanMessage(content=prompt)]
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # 解析批量修复结果
            file_pattern = r'<file\s+path=["\']([^"\']+)["\'][^>]*>\s*```(?:typescript|vue)?\n?(.*?)```'
            for match in re.finditer(file_pattern, response_text, re.DOTALL):
                file_path = match.group(1)
                fixed_content = match.group(2).strip()
                
                full_path = project_path / file_path
                if full_path.exists() and fixed_content:
                    try:
                        # 保存修复前的内容哈希
                        original_content = full_path.read_text(encoding="utf-8")
                        fix_history["content_hashes"][file_path] = hash(original_content)
                        
                        # 写入修复后的内容
                        full_path.write_text(fixed_content, encoding="utf-8")
                        fix_history["fixed_files"][file_path] = True
                        
                        logger.info(f"✅ LLM 批量修复成功: {file_path}")
                        fixed.append(file_path)
                    except Exception as e:
                        logger.error(f"写入修复文件失败 {file_path}: {e}")
                        
        except ImportError as e:
            logger.warning(f"LLM 模块导入失败: {e}")
            # 回退到逐个修复
            for rel_path, full_path in batch:
                if await _fix_file_by_llm(full_path, error_msg):
                    fixed.append(rel_path)
        except Exception as e:
            logger.error(f"批量 LLM 修复失败: {e}")
            # 回退到逐个修复
            for rel_path, full_path in batch:
                if await _fix_file_by_llm(full_path, error_msg):
                    fixed.append(rel_path)
    
    return fixed


async def _generate_stub_view(
    project_path: Path,
    rel_path: str
) -> bool:
    """
    生成简单的 stub Vue 页面文件。
    """
    try:
        path_parts = rel_path.replace("\\", "/").split("/")
        view_name = "GeneratedPage"
        
        for part in path_parts:
            if part.endswith(".vue"):
                view_name = part.replace(".vue", "")
                break
        
        if view_name == "GeneratedPage" and path_parts:
            last_part = path_parts[-1]
            if last_part:
                view_name = last_part.replace("-", "").replace("_", "").title()
        
        full_path = project_path / rel_path
        os.makedirs(full_path.parent, exist_ok=True)
        
        class_name = view_name.lower().replace("-", "").replace("_", "")
        
        stub_content = f'''<script setup lang="ts">
defineProps<{{
  id?: string
}}>()
</script>

<template>
  <div class="{class_name}-page p-6">
    <h1 class="text-2xl font-bold mb-4">{view_name}</h1>
    <p class="text-gray-600">页面内容待生成</p>
  </div>
</template>
'''
        
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(stub_content)
        
        logger.info(f"成功创建 stub 文件: {full_path}")
        return True
        
    except Exception as e:
        logger.error(f"创建 stub 页面失败: {e}")
        return False


def _convert_hyphen_to_camel(match: re.Match, prefix: str = "") -> str:
    """将连字符转换为驼峰命名。"""
    parts = match.group(1).split("-")
    if prefix:
        parts.insert(0, prefix)
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _fix_content_hyphens(
    content: str,
    hyphen_dirs: dict,
    hyphen_modules: dict
) -> str:
    """
    修复文件内容中的连字符引用。
    """
    import re
    new_content = content
    
    # 修复类型名中的连字符 (Rate-Limit-Item -> RateLimitItem)
    for match in re.finditer(rf"([A-Z][a-zA-Z]+(?:-[a-zA-Z]+)+)", new_content):
        type_name = match.group(1)
        camel_type = type_name.replace("-", "")
        new_content = new_content.replace(type_name, camel_type)
    
    # 修复目录名引用
    for dir_name, info in hyphen_dirs.items():
        new_content = new_content.replace(f"'/{dir_name}/", f"'/{info['camel']}/")
        new_content = new_content.replace(f'"/{dir_name}/', f'"/{info["camel"]}/')
        new_content = new_content.replace(f"'/{dir_name}'", f"'/{info['camel']}'")
        new_content = new_content.replace(f'"/{dir_name}"', f'"/{info["camel"]}"')
    
    # 修复模块名引用
    for module_name, info in hyphen_modules.items():
        new_content = new_content.replace(f"'{module_name}'", f"'{info['camel']}'")
        new_content = new_content.replace(f'"{module_name}"', f'"{info["camel"]}"')
        new_content = new_content.replace(f"./{module_name}", f"./{info['camel']}")
        new_content = new_content.replace(f"@{module_name}", f"@{info['camel']}")
    
    return new_content


async def _fix_file_by_llm(file_path: Path, error_msg: str) -> bool:
    """
    使用 LLM 修复文件中的错误。
    读取文件内容，结合错误信息，让 LLM 修复整个文件。
    """
    import re
    
    if not file_path.exists():
        return False
    
    try:
        content = file_path.read_text(encoding="utf-8")
        file_ext = file_path.suffix
        rel_path = str(file_path.relative_to(file_path.parent.parent.parent)) if len(file_path.parts) > 3 else str(file_path)
        
        # 提取该文件相关的错误行
        file_errors = []
        for match in re.finditer(rf"{re.escape(str(file_path))}|{re.escape(file_path.name)}", error_msg):
            start = max(0, match.start() - 50)
            end = min(len(error_msg), match.end() + 200)
            file_errors.append(error_msg[start:end])
        
        errors_text = "\n".join(file_errors[:5])
        
        # 构建修复提示
        if file_ext == ".vue":
            prompt = f"""请修复以下 Vue 文件中的 TypeScript 错误。

文件路径: {rel_path}

文件内容:
```vue
{content}
```

构建错误:
{errors_text}

请直接输出修复后的完整文件内容，确保：
1. 所有 TypeScript 类型定义正确
2. 所有 import/export 语句语法正确
3. 移除所有连字符（使用驼峰命名）
4. 保持原有的业务逻辑不变

只输出修复后的代码，不要解释。"""
        else:
            prompt = f"""请修复以下 TypeScript 文件中的错误。

文件路径: {rel_path}

文件内容:
```typescript
{content}
```

构建错误:
{errors_text}

请直接输出修复后的完整文件内容，确保：
1. 所有类型定义正确
2. 所有 import/export 语句语法正确
3. 移除所有连字符（使用驼峰命名）
4. 保持原有的业务逻辑不变

只输出修复后的代码，不要解释。"""
        
        logger.info(f"调用 LLM 修复文件: {rel_path}")
        
        # 调用 LLM 修复
        try:
            from server.core.llm import get_llm
            from langchain_core.messages import HumanMessage
            
            llm = get_llm(temperature=0.1)
            messages = [HumanMessage(content=prompt)]
            response = await llm.ainvoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            if response_text and len(response_text) > len(content) * 0.5:
                # 提取代码块内容
                code_match = re.search(r"```(?:typescript|vue)?\n?(.*?)```", response_text, re.DOTALL)
                if code_match:
                    fixed_content = code_match.group(1).strip()
                else:
                    # 尝试直接使用响应内容
                    fixed_content = response_text.strip()
                
                # 检查是否包含有效的代码
                if fixed_content and (file_ext == ".vue" or "export" in fixed_content or "import" in fixed_content):
                    file_path.write_text(fixed_content, encoding="utf-8")
                    logger.info(f"✅ LLM 成功修复文件: {rel_path}")
                    return True
                else:
                    logger.warning(f"LLM 返回内容无效，跳过修复: {rel_path}")
        except ImportError as e:
            logger.warning(f"LLM 模块导入失败: {e}")
        except Exception as e:
            logger.error(f"LLM 调用失败: {e}")
        
        return False
        
    except Exception as e:
        logger.error(f"读取文件失败: {file_path}, 错误: {e}")
        return False


async def _fix_hyphen_identifiers(project_path: Path) -> list:
    """
    修复项目中的连字符命名问题。
    例如：rate-limit -> rateLimit, Rate-Limit -> RateLimit
    """
    import re
    fixed_files = []
    
    # 扫描所有可能的目录，包括 views 和 components
    search_dirs = [
        "src/api", "src/types", "src/mocks", "src/stores", 
        "src/composables", "src/components", "src/views"
    ]
    
    # 收集所有连字符文件和目录
    hyphen_modules = {}
    hyphen_dirs = {}
    
    for dir_name in search_dirs:
        target_dir = project_path / dir_name
        if not target_dir.exists():
            continue
        
        # 扫描目录中包含连字符的子目录
        for item in target_dir.iterdir():
            if item.is_dir() and "-" in item.name:
                camel_dir = item.name.replace("-", "")
                hyphen_dirs[item.name] = {
                    "hyphen": item.name,
                    "camel": camel_dir,
                    "path": item,
                    "rel_path": str(item.relative_to(project_path)),
                }
        
        # 扫描目录中的 .ts 文件
        for ts_file in target_dir.rglob("*.ts"):
            if ts_file.stem and "-" in ts_file.stem:
                camel_name = ts_file.stem.replace("-", "")
                hyphen_modules[ts_file.stem] = {
                    "hyphen": ts_file.stem,
                    "camel": camel_name,
                    "path": ts_file,
                    "rel_dir": str(ts_file.parent.relative_to(project_path)),
                }
        
        # 扫描目录中的 .vue 文件
        for vue_file in target_dir.rglob("*.vue"):
            if vue_file.stem and "-" in vue_file.stem:
                camel_name = vue_file.stem.replace("-", "")
                hyphen_modules[vue_file.stem] = {
                    "hyphen": vue_file.stem,
                    "camel": camel_name,
                    "path": vue_file,
                    "rel_dir": str(vue_file.parent.relative_to(project_path)),
                }
    
    all_hyphen = {**hyphen_dirs, **hyphen_modules}
    
    if not all_hyphen:
        logger.info("未发现连字符文件或目录")
        return fixed_files
    
    logger.info(f"发现连字符文件/目录: {list(all_hyphen.keys())}")
    
    # 1. 先重命名目录（需要先处理，否则子文件路径会变化）
    for dir_name, info in hyphen_dirs.items():
        hyphen_path = info["path"]
        camel_dir = info["camel"]
        camel_path = hyphen_path.parent / camel_dir
        
        if hyphen_path.exists() and not camel_path.exists():
            # 先修复目录内所有文件的内容
            for ts_file in hyphen_path.rglob("*.ts"):
                content = ts_file.read_text(encoding="utf-8")
                new_content = _fix_content_hyphens(content, hyphen_dirs, hyphen_modules)
                if new_content != content:
                    ts_file.write_text(new_content, encoding="utf-8")
                    logger.info(f"✅ 修复文件内容: {ts_file.relative_to(project_path)}")
            
            for vue_file in hyphen_path.rglob("*.vue"):
                content = vue_file.read_text(encoding="utf-8")
                new_content = _fix_content_hyphens(content, hyphen_dirs, hyphen_modules)
                if new_content != content:
                    vue_file.write_text(new_content, encoding="utf-8")
                    logger.info(f"✅ 修复 Vue 文件内容: {vue_file.relative_to(project_path)}")
            
            # 重命名目录
            hyphen_path.rename(camel_path)
            logger.info(f"✅ 重命名目录: {info['rel_path']} -> {str(camel_path.relative_to(project_path))}")
            fixed_files.append(f"{info['rel_path']}/ (重命名为 {camel_path.name})")
    
    # 2. 重命名所有 .ts 和 .vue 文件并修复内容
    for module_name, info in all_hyphen.items():
        if module_name in hyphen_dirs:
            continue  # 目录已处理
        
        hyphen_file = info["path"]
        if not hyphen_file.exists():
            continue
            
        camel_name = info["camel"]
        is_vue = hyphen_file.suffix == ".vue"
        
        content = hyphen_file.read_text(encoding="utf-8")
        new_content = _fix_content_hyphens(content, hyphen_dirs, hyphen_modules)
        
        # 修复文件自身的连字符
        new_content = new_content.replace(module_name, camel_name)
        
        # 修复导出声明
        new_content = re.sub(
            rf"export const {re.escape(module_name)}(Api|Module|Item)?",
            lambda m: f"export const {camel_name}{m.group(1) or ''}",
            new_content
        )
        
        hyphen_file.write_text(new_content, encoding="utf-8")
        
        # 重命名文件
        ext = ".vue" if is_vue else ".ts"
        new_file = hyphen_file.parent / f"{camel_name}{ext}"
        hyphen_file.rename(new_file)
        
        logger.info(f"✅ 重命名文件: {module_name}{ext} -> {camel_name}{ext}")
        fixed_files.append(f"{info['rel_dir']}/{camel_name}{ext}")
    
    # 3. 更新 src/api/index.ts
    index_file = project_path / "src" / "api" / "index.ts"
    if index_file.exists():
        content = index_file.read_text(encoding="utf-8")
        new_content = content
        for module_name, info in hyphen_modules.items():
            new_content = new_content.replace(module_name, info["camel"])
            new_content = re.sub(
                rf"from ['\"]\./{re.escape(module_name)}['\"]",
                f"from './{info['camel']}'",
                new_content
            )
        
        if new_content != content:
            index_file.write_text(new_content, encoding="utf-8")
            logger.info(f"✅ 已修复 index.ts 中的连字符导入")
            fixed_files.append("src/api/index.ts")
            new_content = re.sub(
                rf"from ['\"]\./{re.escape(module_name)}['\"]",
                f"from './{info['camel']}'",
                new_content
            )
        
        if new_content != content:
            index_file.write_text(new_content, encoding="utf-8")
            logger.info(f"✅ 已修复 index.ts 中的连字符导入")
            fixed_files.append("src/api/index.ts")
    
    # 3. 修复其他目录中的文件引用
    for dir_name in ["stores", "composables", "mocks", "views", "components"]:
        target_dir = project_path / "src" / dir_name
        if not target_dir.exists():
            continue
        
        for ts_file in target_dir.rglob("*.ts"):
            if not ts_file.is_file():
                continue
            
            content = ts_file.read_text(encoding="utf-8")
            new_content = content
            
            for module_name, info in hyphen_modules.items():
                new_content = new_content.replace(f"'{module_name}'", f"'{info['camel']}'")
                new_content = new_content.replace(f'"{module_name}"', f'"{info["camel"]}"')
            
            if new_content != content:
                ts_file.write_text(new_content, encoding="utf-8")
                logger.info(f"✅ 已修复 {ts_file.relative_to(project_path)} 中的引用")
                fixed_files.append(str(ts_file.relative_to(project_path)))
    
    # 4. 修复 Vue 文件中的引用
    views_dir = project_path / "src" / "views"
    if views_dir.exists():
        for vue_file in views_dir.rglob("*.vue"):
            if not vue_file.is_file():
                continue
            
            content = vue_file.read_text(encoding="utf-8")
            new_content = content
            
            for module_name, info in hyphen_modules.items():
                new_content = new_content.replace(f"'{module_name}'", f"'{info['camel']}'")
                new_content = new_content.replace(f'"{module_name}"', f'"{info["camel"]}"')
            
            if new_content != content:
                vue_file.write_text(new_content, encoding="utf-8")
                logger.info(f"✅ 已修复 {vue_file.relative_to(project_path)} 中的引用")
                fixed_files.append(str(vue_file.relative_to(project_path)))
    
    logger.info(f"连字符修复完成，共修复 {len(fixed_files)} 个文件")
    return fixed_files


async def _fix_lint_errors(project_path: str, lint_msg: str) -> list:
    """
    修复 lint 错误。
    """
    import re
    from pathlib import Path
    
    fixed = []
    project_path = Path(project_path)
    
    unused_vars = re.findall(r"'([^']+)' is defined but never used", lint_msg)
    if unused_vars:
        logger.info(f"未使用变量: {unused_vars}")
    
    missing_deps = re.findall(r"'([^']+)' is not defined", lint_msg)
    if missing_deps:
        logger.warning(f"未定义变量: {missing_deps}")
    
    return fixed


def save_memory_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """将本次会话的短期与长期记忆持久化到磁盘。"""
    logger.info("Saving memory...")
    
    try:
        from .memory import ShortTermMemory, LongTermMemory
        
        execution_id = state.get("execution_id")
        tenant_id = state.get("tenant_id", "default")
        user_id = state.get("user_id", "default")
        
        if execution_id:
            short_term = ShortTermMemory(
                session_id=execution_id,
                tenant_id=tenant_id,
                user_id=user_id,
            )
            
            if state.get("tech_stack"):
                short_term.tech_stack = state["tech_stack"]
            if state.get("coverage_matrix"):
                short_term.coverage_matrix = state["coverage_matrix"]
            if state.get("document_summary"):
                short_term.document_summary = state["document_summary"]
            if state.get("module_plans"):
                short_term.module_plan = [
                    plan if isinstance(plan, ModulePlan) else ModulePlan(**plan)
                    for plan in state["module_plans"]
                ]
            if state.get("execution_trace"):
                short_term.execution_trace = state["execution_trace"]
            if state.get("error_trace"):
                short_term.error_trace = state["error_trace"]
            if state.get("generated_artifacts"):
                short_term.generated_artifacts = state["generated_artifacts"]
            
            short_term.save()
            logger.info("Short-term memory saved for session: {}", execution_id)
        
        long_term = LongTermMemory()
        long_term.save()
        logger.info("Long-term memory persisted")
        
    except Exception as exc:
        logger.exception("Failed to save memory")
        state["error_message"] = f"Memory persistence failed: {exc}"
    
    return state


def return_result_node(state: FrontendProjectCreateState) -> FrontendProjectCreateState:
    """整理最终响应结果，包含验证评分与生成摘要。"""
    logger.info("Returning result...")

    project_path = state.get("project_path")
    status = state.get("status")
    error_message = state.get("error_message")
    build_ok = state.get("build_ok", False)

    success = build_ok and status in ["verification_passed", "modules_generated"]

    state["result"] = {
        "success": success,
        "project_path": project_path,
        "status": status,
        "error": error_message,
        "modules_generated": state.get("total_modules", 0),
        "files_generated": len(state.get("output_artifacts", [])),
        "verification_score": state.get("verification_score", 0.0),
        "verification_errors": state.get("verification_errors", []),
        "verification_warnings": state.get("verification_warnings", []),
        "vercel_url": state.get("vercel_url", ""),
        "download_url": state.get("download_url", ""),
        "install_ok": state.get("install_ok", False),
        "build_ok": build_ok,
        "build_msg": state.get("build_msg", ""),
        "lint_ok": state.get("lint_ok", False),
        "lint_msg": state.get("lint_msg", ""),
        "dev_ok": state.get("dev_ok", False),
        "dev_msg": state.get("dev_msg", ""),
        "execution_id": state.get("execution_id"),
    }

    return state


app = create_graph()
