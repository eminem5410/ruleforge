using RuleForge.Core.Syntax;

namespace RuleForge.Core.Evaluation;

public record Decision(string RuleId, int RuleVersion, int LanguageVersion, bool Matched, List<ActionNode> Actions);
