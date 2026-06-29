"""kitfox-config reference resolver (Epic B).

Pure function of the config tree: resolve_namespace(tree, cluster, namespace)
deep-merges the 8 precedence layers (§3) and emits the resolved namespace +
per-tenant model (§5.2). Versions/coordinates are deliberately absent.
"""

from resolver.model import ResolvedNamespace, ResolvedTenant
from resolver.resolve import resolve_namespace, emit_json

__all__ = ["ResolvedNamespace", "ResolvedTenant", "resolve_namespace", "emit_json"]
