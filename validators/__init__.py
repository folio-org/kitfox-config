"""Epic D cross-level validators. run_tree(root, app_index) walks every
(cluster, namespace) and returns {(cluster, namespace): [Violation, ...]}."""

from validators.core import Violation
from validators.runner import run_namespace, run_tree

__all__ = ["Violation", "run_namespace", "run_tree"]
