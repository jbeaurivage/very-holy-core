alias t:= test

test *TEST:
	veryl build --quiet
	cargo test {{TEST}}