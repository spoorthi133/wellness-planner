"""
Constraint Engine Module

The Constraint Engine is responsible for analyzing user constraints
and preparing constraint signals for downstream nodes in the LangGraph.

Core Responsibilities:
1. Normalize raw constraints into structured system constraints
2. Calculate constraint severity and interaction effects
3. Cluster related constraints
4. Detect constraint conflicts
5. Determine overall constraint pressure level
6. Prepare constraint signals for downstream processing

Architecture:
- constraint_models.py: Data structures and models
- constraint_utils.py: Utility functions for constraint operations
- constraint_analyzer.py: Orchestration logic
- constraint_node.py: LangGraph node integration

Position in Workflow:
User Input
   ↓
Constraint Analyzer ← THIS MODULE
   ↓
Constraint Forecast Engine
   ↓
Energy Budget Manager
   ↓
Environment Adapter

Integration:
- Import constraint_analyzer_node for LangGraph integration
- Use ConstraintAnalyzer class for programmatic analysis

Example Usage:
    from constraint_analyzer import ConstraintAnalyzer
    
    analyzer = ConstraintAnalyzer()
    result = analyzer.analyze(
        raw_constraints=[...],
        life_mode="maintenance",
    )
    score = result.constraint_score
    pressure = result.constraint_pressure_level
"""

from constraint_models import (
    ConstraintCategory,
    ConstraintSeverityLevel,
    NormalizedConstraint,
    ConstraintCluster,
    ConstraintConflict,
    ConstraintScoringMetrics,
    ConstraintAnalysisContext,
    ConstraintAnalysisResult,
    ConstraintValidationResult,
)
from constraint_analyzer import ConstraintAnalyzer
from constraint_node import constraint_analyzer_node

__all__ = [
    # Models
    "ConstraintCategory",
    "ConstraintSeverityLevel",
    "NormalizedConstraint",
    "ConstraintCluster",
    "ConstraintConflict",
    "ConstraintScoringMetrics",
    "ConstraintAnalysisContext",
    "ConstraintAnalysisResult",
    "ConstraintValidationResult",
    # Main components
    "ConstraintAnalyzer",
    "constraint_analyzer_node",
]

__version__ = "1.0.0"
__author__ = "Wellness Agent Development Team"
__description__ = "Constraint-First Wellness Planning - Constraint Engine Module"
