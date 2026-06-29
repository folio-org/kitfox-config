"""Epic D cross-level validators. run_tree(root, app_index) walks every
(cluster, namespace) and returns {(cluster, namespace): [Violation, ...]}."""

from validators.core import Violation

try:
    from validators.runner import run_namespace, run_tree
except ImportError:
    pass  # runner is implemented in a later task

__all__ = ["Violation", "run_namespace", "run_tree"]
