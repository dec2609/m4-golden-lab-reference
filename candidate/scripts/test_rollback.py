"""Rollback uses the same gated CLI as deployment; no parallel legacy implementation."""
from deploy_staging import main
if __name__=='__main__':raise SystemExit(main(rollback=True))
