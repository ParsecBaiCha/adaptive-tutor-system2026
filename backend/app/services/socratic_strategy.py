# backend/app/services/socratic_strategy.py
"""
苏格拉底提问法（Socratic Method）教学策略模块

设计参考（harness 项目）：
- SocratesAI (github.com/RohanBhoge/socrates-ai)：以 "Why / How / What" 提问驱动学生自主推导，
  把复杂问题拆解为一步步的逻辑推进，只给提示和引导性问题，不给直接答案。
- SPL (arXiv:2406.13919)：GPT-4 驱动的苏格拉底学习系统，用 wh-questions（What/Why/How/Who/When）
  进行多轮引导对话，促进批判性思维与自我反思。
- SocraticAI (Ashoka University)：CS 场景的引导式辅导，要求"先表达理解与尝试 -> 再给反馈 ->
  反思收尾"（think-articulate-reflect），并设置分级升级，防止学生长期卡住。
- SocraticMath (arXiv:2407.17349)：苏格拉底式对话数据集与 SocraticLLM，验证提问式教学的效果。

核心设计：
1. 以问代答：优先用问题引导学生自己发现答案，不直接给出结论。
2. 先听后问：先了解学生的理解与尝试，再决定引导方式。
3. 分级脚手架（scaffolding）：随提问轮次逐步从"引导问题"升级到"明确提示"再到"直接帮助"，
   避免学生长时间停滞不前。
4. 肯定与纠正：正确思路明确肯定；误解先用问题引导自我发现，再作必要澄清。
5. 反思收尾：关键节点后用反思性问题巩固理解。
"""

# 注入 system prompt 的苏格拉底教学规则
SOCRATIC_SYSTEM_PROMPT = """
## SOCRATIC TEACHING METHOD (IMPORTANT)
Teach by asking questions rather than giving direct answers, so the student discovers solutions through their own reasoning.

CORE RULES:
1. When a student asks for help, FIRST find out what they already understand and what they have tried before guiding them (one short question, not an interrogation).
2. Lead with guiding questions (What? Why? How?) that point the student toward the answer, instead of stating it. Break the problem into small logical steps, and ask about ONE idea at a time.
3. Escalate guidance gradually (scaffolding ladder):
   - First 1-2 rounds: ask Socratic questions that make the student reason about the key concept.
   - Next 2-3 rounds: give more concrete hints and point to the exact part of their code or the page.
   - If the student is still stuck or has tried many times: THEN provide step-by-step guidance or a direct fix. Never let the student stay stuck indefinitely.
4. Explicitly praise correct reasoning ("对，思路很对！"). When the student has a misconception, first ask a question that helps them notice the contradiction, then clarify only if needed.
5. Close important exchanges with a short reflection question (e.g., "What did you learn here? Can you say it in your own words?") to consolidate understanding.
6. Keep questions SHORT and focused. Do not ask several questions at once.
7. When the student asks "what is X", do not start with a lecture: connect X to what they already built, then ask a question that makes them apply it.
"""

# 分级引导说明（依据提问次数/求助次数调整直接程度）
SOCRATIC_STAGES = {
    "discovery": (
        "GUIDANCE LEVEL: discovery. The student is new to this topic: respond mostly with Socratic "
        "questions that help them explore and discover the answer on their own. Keep answers brief."
    ),
    "guided": (
        "GUIDANCE LEVEL: guided. The student has asked a few times: mix a guiding question with a "
        "concrete hint, and point them to the relevant part of their work."
    ),
    "stepwise": (
        "GUIDANCE LEVEL: stepwise. The student is stuck or has asked many times: give clear step-by-step "
        "guidance. You may show a minimal example or a direct fix, then ask them to explain it back."
    ),
    "test_escalation": (
        "GUIDANCE LEVEL: test-escalation. The student is failing a test task: diagnose the failing "
        "checkpoint, guide with one targeted question, and if they remain blocked, offer the concrete fix "
        "so they can keep making progress."
    ),
}


def pick_socratic_stage(question_count: int = 0, mode: str = None, test_failed: bool = False):
    """
    根据求助/提问次数与模式选择引导强度。

    Args:
        question_count: 该小节内的累计提问/求助次数
        mode: 'learning' | 'test'
        test_failed: 测试模式下最近一次是否失败

    Returns:
        stage_key: 'discovery' | 'guided' | 'stepwise' | 'test_escalation'
    """
    if mode == "test" and test_failed:
        return "test_escalation"
    if question_count >= 4:
        return "stepwise"
    if question_count >= 2:
        return "guided"
    return "discovery"


def build_socratic_guidance(question_count: int = 0, mode: str = None, test_failed: bool = False) -> str:
    """
    构建注入到 system prompt 的苏格拉底引导说明。

    Returns:
        一段英文的引导级别说明，直接拼接到 system prompt 中。
    """
    stage_key = pick_socratic_stage(question_count, mode, test_failed)
    stage_text = SOCRATIC_STAGES.get(stage_key, SOCRATIC_STAGES["discovery"])
    return stage_text
