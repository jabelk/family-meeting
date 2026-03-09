#!/usr/bin/env bash
# Helper script for NUC home-server deployment. Not used for Railway deployment.
# For Railway, CI/CD auto-deploys on push to main (see .github/workflows/ci.yml).
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
  chat-logs)
    # Retrieve archived conversation logs from NUC
    # Usage: ./scripts/nuc.sh chat-logs [date|latest|start end]
    ARCHIVE_DIR="$DIR/data/conversation_archives"
    LOCAL_DIR="$(dirname "$0")/../data/conversation_archives"
    mkdir -p "$LOCAL_DIR"

    if [ -z "${2:-}" ]; then
      # List available archives
      ssh "$NUC" "ls -1 $ARCHIVE_DIR/conversations-*.json 2>/dev/null | sed 's|.*/conversations-||;s|\.json||' | sort"
    elif [ "$2" = "latest" ]; then
      # Pull most recent archive
      LATEST=$(ssh "$NUC" "ls -1 $ARCHIVE_DIR/conversations-*.json 2>/dev/null | sort | tail -1")
      if [ -z "$LATEST" ]; then
        echo "No archives found on NUC"
        exit 1
      fi
      scp "$NUC:$LATEST" "$LOCAL_DIR/"
      echo "Retrieved: $(basename "$LATEST")"
    elif [ -n "${3:-}" ]; then
      # Date range: pull all archives between start and end dates
      START="$2"
      END="$3"
      FILES=$(ssh "$NUC" "for f in $ARCHIVE_DIR/conversations-*.json; do d=\$(basename \"\$f\" | sed 's/conversations-//;s/.json//'); if [[ \"\$d\" >= \"$START\" && \"\$d\" <= \"$END\" ]]; then echo \"\$f\"; fi; done 2>/dev/null")
      if [ -z "$FILES" ]; then
        echo "No archives found for $START to $END"
        exit 1
      fi
      COUNT=0
      while IFS= read -r f; do
        scp "$NUC:$f" "$LOCAL_DIR/"
        COUNT=$((COUNT + 1))
      done <<< "$FILES"
      echo "Retrieved $COUNT archives ($START to $END)"
    else
      # Single date
      FILE="$ARCHIVE_DIR/conversations-$2.json"
      scp "$NUC:$FILE" "$LOCAL_DIR/" 2>/dev/null || { echo "No archive found for $2"; exit 1; }
      echo "Retrieved: conversations-$2.json"
    fi
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
    echo "  chat-logs           List archived conversation dates"
    echo "  chat-logs <date>    Pull archive for YYYY-MM-DD"
    echo "  chat-logs latest    Pull most recent archive"
    echo "  chat-logs <s> <e>   Pull archives for date range"
    ;;
esac
