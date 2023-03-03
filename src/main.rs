use clap::{Parser, Subcommand};
use clap_verbosity_flag::Verbosity;
use mystuff::datastore::local::LocalDataStore;
use mystuff::datastore::DataStore;
use mystuff::links::{add_link, list_links};

/// Mystuff client. Manages links, the wiki, etc.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
pub struct Cli {
    /// mystuff data directory, default: ~/.mystuff/
    #[arg(short, long, value_name = "PATH")]
    pub data: Option<String>,

    #[clap(flatten)]
    verbose: Verbosity,

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

fn handle_link<T: DataStore>(datastore: T, add: Option<String>) {
    if add.is_some() {
        add_link(datastore, add.unwrap())
    } else {
        list_links(datastore);
    }
}

fn main() {
    let args = Cli::parse();

    env_logger::Builder::new()
        .filter_level(args.verbose.log_level_filter())
        .init();

    log::error!("Engines exploded");
    log::warn!("Engines smoking");
    log::info!("Engines exist");
    log::debug!("Engine temperature is 200 degrees");
    log::trace!("Engine subsection is 300 degrees");

    log::debug!("==> cli arguments: {:?}", args);

    let datastore = LocalDataStore::new(args.data);

    log::debug!("==> data directory: {:?}", datastore.path);

    match args.command {
        None => {
            log::info!("==> no command");
        }
        Some(command) => match command {
            Commands::Link { add } => handle_link(datastore, add),
        },
    }
}
