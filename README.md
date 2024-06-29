# Rust compiler output filter

*tl;dr* More concise `rustc` output for intermediate and advanced developers.

If you use Rust's `cargo build` from the command-line then you are probably aware that the warnings and errors, while helpful for newcomers, can be **very verbose**. A simple unused variable warning is 7 lines long and some rather straightforward errors can number in the dozens lines. This can make it difficult to quickly find the spot you need to fix in your code.

Rust's `cargo` tool has the option `--message-format short` which turns **every** warning and error into **one line**, and as this is 100% guaranteed to work, it may very well be the fix you are looking for.

This project provides an alternative in a single script that modifies the verbose default `rustc` output in an opinionated manner, one warning at a time.

The filter tool in this project condenses common and basic warnings into one line, adds useful hints for some errors while keeping them relatively concise, and finally shows the most complex errors in their original verbose format. Whatever seems the most helpful for the developer.

To make use of this tool, you will probably want to modify the filters and add your own, so the development focus is in keeping the script clear and hackable. Consider forking rather than sending a pull request.

## Usage

*tl;dr* Instead of `cargo check` (or `build`, `run`, `test`), do `filter-cargo check`.

Changing `rustc` output to "JSON diagnostic rendered ANSI" adds a bunch of information that can be stripped away using eg the [jq](https://jqlang.github.io/jq/) tool. Running the following produces identical output to `cargo check` (same for `run` and `build`):

```sh
cargo check --message-format=json-diagnostic-rendered-ansi | jq --raw-output 'select(.reason=="compiler-message") | .message.rendered'
```

The tool in this project functions by filtering the JSONL in the middle of the pipeline like this:

```sh
cargo check --message-format=json-diagnostic-rendered-ansi | filter-rustc | jq --raw-output 'select(.reason=="compiler-message") | .message.rendered'
```

That is quite awkward to type so there is a helper script that accomplishes the same with `filter-cargo check`. This also avoids the `jq` dependency.

## Detailed setup

Developed and tested only on Linux.

Install [Rust](https://www.rust-lang.org/tools/install). Then run:

```sh
git clone https://github.com/pekkaran/filter-rustc.git
cd filter-rustc
chmod +x filter-rustc filter-cargo
```

Add eg in your `.bashrc`: `PATH="$PATH:/path/to/filter-rustc"` and open a new terminal.

For example if you normally run your program as `cargo run -- --enigmaticNumber 23`, then the replacement you need is:

```sh
cd my-rust-project
filter-cargo run -- --enigmaticNumber 23
```
