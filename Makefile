.PHONY: run

run:
	@sh -c ' \
		pipenv run backend & backend_pid=$$!; \
		pipenv run frontend & frontend_pid=$$!; \
		trap "echo; echo Stopping processes...; kill $$backend_pid $$frontend_pid" SIGINT TERM; \
		wait \
	'
