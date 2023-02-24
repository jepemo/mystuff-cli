mod args;
mod links;

use args::{Cli, Commands};
use clap::Parser;
use links::handle_link;
use std::fs;
use std::path::Path;

fn main() {
    let args = Cli::parse();

    if args.verbose {
        println!("==> cli arguments: {:?}", args);
    }

    let default_path = shellexpand::tilde("~/.mystuff");
    let data = args
        .data
        .clone()
        .unwrap_or_else(|| String::from(default_path.clone()));

    if !Path::new(&data).is_dir() {
        match fs::create_dir(&data) {
            Ok(_file) => {
                if args.verbose {
                    println!("==> creating directory {}", &data)
                }
            }
            Err(error) => {
                panic!("cannot create directory; {}, error: {:?}", &data, error);
            }
        }
    }

    if args.verbose {
        println!("==> data directory: {:?}", data);
    }

    match args.command {
        None => {
            if args.verbose {
                println!("==> no command");
            }
        }
        Some(command) => match command {
            Commands::Link { add } => handle_link(data, add, args.verbose),
        },
    }
}
