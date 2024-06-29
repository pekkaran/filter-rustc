# Rust compiler output filter

If you use Rust's `cargo build` from the command-line then you are probably aware that the warnings and errors, while helpful for newcomers, can be **very verbose**. A simple unused variable warning is 7 lines long and some rather straightforward errors can number in the dozens. This can make it difficult to spot the root error or clutter the output with warnings you don't intend to fix immediately.

The `cargo` tool has the option `--message-format short` which turns **every** warning and error into **one line**, and as this is 100% guaranteed to work, it may very well be what you are looking for.

This project consists of a single script that modifies the default and verbose `rustc` output in an opinionated manner, one warning at a time. If no filter for a warning hasn't been implemented in the script the original verbose output will be shown.

The filter in this project condenses common and basic warnings into one line, adds useful hints for some errors while keeping them relatively concise, and finally shows the most complex errors in their original verbose format. Whatever seems the most helpful for the developer.

To make use of this tool, you will probably want to modify the filters and add your own, so the development focus is in keeping the script clear and hackable. Consider forking rather than sending a pull request.
