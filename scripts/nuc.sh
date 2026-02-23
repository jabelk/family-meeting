#!/usr/bin/env bash
# Helper commands for managing the family-meeting stack on the NUC
# Usage: ./scripts/nuc.sh <command>

set -e

NUC="warp-nuc"
DIR="~/family-meeting"

case "${1:-help}" in
  logs)
    # Show recent logs, optionally for a specific service
    # Usage: ./scripts/nuc.sh logs [service] [lines]
    SERVICE="${2:-fastapi}"
    LINES="${3:-30}"
    ssh "$NUC" "docker compose -f $DIR/docker-compose.yml logs $SERVICE --tail $LINES"
    ;;
  follow)
    # Follow logs in real-time
    # Usage: ./scripts/nuc.sh follow [service]
    SERVICE="${2:-fastapi}"
    ssh "$NUC" "docker compose -f $DIR/docker-compose.yml logs $SERVICE -f --tail 10"
    ;;
  ps)
    # Show container status
    ssh "$NUC" "docker compose -f $DIR/docker-compose.yml ps"
    ;;
  restart)
    # Restart a service (or all)
    # Usage: ./scripts/nuc.sh restart [service]
    SERVICE="${2:-}"
    ssh "$NUC" "cd $DIR && docker compose restart $SERVICE"
    ;;
  deploy)
    # Pull latest code, rebuild and restart
    ssh "$NUC" "cd $DIR && git pull && docker compose up -d --build"
    ;;
  env)
    # Push .env from laptop to NUC and recreate fastapi
    scp "$(dirname "$0")/../.env" "$NUC:$DIR/.env"
    ssh "$NUC" "cd $DIR && docker compose up -d --force-recreate fastapi"
    echo "Updated .env and restarted fastapi"
    ;;
  ssh)
    # Open an interactive SSH session
    ssh "$NUC"
    ;;
  shell)
    # Open a shell inside a container
    # Usage: ./scripts/nuc.sh shell [service]
    SERVICE="${2:-fastapi}"
    ssh "$NUC" "docker compose -f $DIR/docker-compose.yml exec $SERVICE sh"
    ;;
  help|*)
    echo "Usage: ./scripts/nuc.sh <command>"
    echo ""
    echo "Commands:"
    echo "  logs [service] [n]  Show last n log lines (default: fastapi, 30)"
    echo "  follow [service]    Follow logs in real-time"
    echo "  ps                  Show container status"
    echo "  restart [service]   Restart service (or all)"
    echo "  deploy              Pull, rebuild, and restart on NUC"
    echo "  env                 Push .env to NUC and restart fastapi"
    echo "  ssh                 Open SSH session to NUC"
    echo "  shell [service]     Open shell inside container"
    ;;
esac
