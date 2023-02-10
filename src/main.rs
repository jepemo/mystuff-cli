use clap::{Parser, Subcommand};
use std::fs::File;
use std::path::Path;

/// Mystuff client. Manages links, the wiki, etc.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// mystuff data directory, default: ~/.mystuff/
    #[arg(short, long, value_name = "PATH")]
    data: Option<String>,

    /// Verbose mode
    #[arg(short, long)]
    verbose: bool,

    #[command(subcommand)]
    command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Manage links
    Link {
        /// Add new link
        #[arg(short, long)]
        add: bool,
    },
}

fn main() {
    let args = Cli::parse();

    if args.verbose {
        println!("==> cli arguments: {:?}", args);
    }

    let default_path = shellexpand::tilde("~/.mystuff");
    let data = args
        .data
        .clone()
        .unwrap_or_else(|| String::from(default_path));

    if args.verbose {
        println!("==> data directory: {:?}", data);
    }

    let links_file = Path::new(&data).join("links.jsonl");
    if !links_file.exists() {
        File::create(links_file).unwrap_or_else(|error| {
            panic!("Problem creating the file: {:?}", error);
        });
    }

    match args.command {
        None => {
            if args.verbose {
                println!("==> no command");
            }
        }
        Some(command) => {
            println!("{:?}", command);
        }
    }

    // let a = args.command.unwrap();

    // println!("{:?}", links_file);

    // let paths = fs::read_dir(default_path.as_ref()).unwrap();
    // for path in paths {
    //     println!("Name: {}", path.unwrap().path().display())
    // }
}
