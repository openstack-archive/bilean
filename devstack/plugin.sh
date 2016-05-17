# bilean.sh - Devstack extras script to install bilean

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

echo_summary "bilean's plugin.sh was called..."
source $DEST/bilean/devstack/lib/bilean
(set -o posix; set)

if is_service_enabled bl-api bl-eng bl-sch bl-noti; then
    if [[ "$1" == "stack" && "$2" == "pre-install" ]]; then
        echo_summary "Before Installing bilean"
        mkdir -p $SCREEN_LOGDIR
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing bilean"
        install_bilean
        echo_summary "Installing bileanclient"
        install_bileanclient
        cleanup_bilean
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring bilean"
        configure_bilean

        if is_service_enabled key; then
            create_bilean_accounts
        fi

    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        # Initialize bilean
        init_bilean

        # Start the bilean API and bilean taskmgr components
        echo_summary "Starting bilean"
        start_bilean
    fi

    if [[ "$1" == "unstack" ]]; then
        stop_bilean
    fi

    if [[ "$1" == "clean" ]]; then
        cleanup_bilean
    fi
fi

# Restore xtrace
$XTRACE
