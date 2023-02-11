use clap::{Parser, Subcommand};

/// Mystuff client. Manages links, the wiki, etc.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    /// mystuff data directory, default: ~/.mystuff/
    #[arg(short, long, value_name = "PATH")]
    pub data: Option<String>,

    /// Verbose mode
    #[arg(short, long)]
    pub verbose: bool,

    #[command(subcommand)]
    pub command: Option<Commands>,
}

#[derive(Subcommand, Debug)]
pub enum Commands {
    /// Manage links
    Link {
        /// Add new link
        #[arg(short, long)]
        add: Option<String>,
    },
}
