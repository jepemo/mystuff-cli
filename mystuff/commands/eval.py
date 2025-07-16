"""
Eval command for MyStuff CLI
Manages self-evaluation entries with YAML storage and reporting
"""
import typer
from pathlib import Path
from typing_extensions import Annotated
from typing import List, Optional, Dict
import os
import yaml
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

def get_mystuff_dir() -> Path:
    """Get the mystuff data directory from config or environment"""
    mystuff_home = os.getenv("MYSTUFF_HOME")
    if mystuff_home:
        return Path(mystuff_home).expanduser().resolve()
    return Path.home() / ".mystuff"

def get_eval_dir() -> Path:
    """Get the path to the eval directory"""
    return get_mystuff_dir() / "eval"

def ensure_eval_dir_exists():
    """Ensure the eval directory exists"""
    eval_dir = get_eval_dir()
    eval_dir.mkdir(parents=True, exist_ok=True)

def get_eval_filename(date: str) -> str:
    """Generate filename for evaluation entries (grouped by month)"""
    # Parse date to get year and month
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        return f"{date_obj.year}-{date_obj.month:02d}.yaml"
    except ValueError:
        # Fallback to current month if invalid date
        now = datetime.now()
        return f"{now.year}-{now.month:02d}.yaml"

def get_editor() -> str:
    """Get the editor from environment or config"""
    return os.getenv("EDITOR", "vim")

def is_fzf_available() -> bool:
    """Check if fzf is available on the system"""
    try:
        subprocess.run(["fzf", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def load_evaluations_from_file(file_path: Path) -> List[dict]:
    """Load evaluations from a YAML file"""
    if not file_path.exists():
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if data is None:
                return []
            return data if isinstance(data, list) else []
    except Exception as e:
        typer.echo(f"Error loading evaluations from {file_path}: {e}", err=True)
        return []

def save_evaluations_to_file(file_path: Path, evaluations: List[dict]):
    """Save evaluations to a YAML file"""
    ensure_eval_dir_exists()
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(evaluations, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        typer.echo(f"Error saving evaluations to {file_path}: {e}", err=True)
        raise typer.Exit(code=1)

def get_all_evaluations() -> List[dict]:
    """Get all evaluations from all YAML files"""
    eval_dir = get_eval_dir()
    if not eval_dir.exists():
        return []
    
    all_evaluations = []
    for file_path in eval_dir.glob("*.yaml"):
        evaluations = load_evaluations_from_file(file_path)
        for eval_entry in evaluations:
            eval_entry['file_path'] = file_path
            all_evaluations.append(eval_entry)
    
    # Sort by date (newest first)
    all_evaluations.sort(key=lambda x: x.get('date', ''), reverse=True)
    return all_evaluations

def find_evaluation_by_date_and_category(date: str, category: str) -> Optional[dict]:
    """Find a specific evaluation by date and category"""
    filename = get_eval_filename(date)
    file_path = get_eval_dir() / filename
    
    evaluations = load_evaluations_from_file(file_path)
    for eval_entry in evaluations:
        if eval_entry.get('date') == date and eval_entry.get('category') == category:
            eval_entry['file_path'] = file_path
            return eval_entry
    
    return None

def add_or_update_evaluation(date: str, category: str, score: int, comments: str = ""):
    """Add or update an evaluation entry"""
    filename = get_eval_filename(date)
    file_path = get_eval_dir() / filename
    
    evaluations = load_evaluations_from_file(file_path)
    
    # Check if evaluation already exists
    existing_index = None
    for i, eval_entry in enumerate(evaluations):
        if eval_entry.get('date') == date and eval_entry.get('category') == category:
            existing_index = i
            break
    
    # Create new evaluation entry
    new_entry = {
        'date': date,
        'category': category,
        'score': score,
        'comments': comments
    }
    
    if existing_index is not None:
        # Update existing entry
        evaluations[existing_index] = new_entry
    else:
        # Add new entry
        evaluations.append(new_entry)
    
    # Sort by date
    evaluations.sort(key=lambda x: x.get('date', ''))
    
    # Save to file
    save_evaluations_to_file(file_path, evaluations)
    
    return existing_index is not None

def remove_evaluation(date: str, category: str) -> bool:
    """Remove an evaluation entry"""
    filename = get_eval_filename(date)
    file_path = get_eval_dir() / filename
    
    evaluations = load_evaluations_from_file(file_path)
    
    # Find and remove the evaluation
    for i, eval_entry in enumerate(evaluations):
        if eval_entry.get('date') == date and eval_entry.get('category') == category:
            evaluations.pop(i)
            
            # Save updated list
            if evaluations:
                save_evaluations_to_file(file_path, evaluations)
            else:
                # Remove file if empty
                if file_path.exists():
                    file_path.unlink()
            
            return True
    
    return False

def select_evaluation_with_fzf(evaluations: List[dict]) -> Optional[dict]:
    """Use fzf to select an evaluation interactively"""
    if not evaluations:
        return None
    
    # Create options for fzf
    options = []
    for eval_entry in evaluations:
        date = eval_entry.get('date', '')
        category = eval_entry.get('category', '')
        score = eval_entry.get('score', 0)
        comments = eval_entry.get('comments', '')
        
        # Truncate comments for display
        comments_preview = comments[:30] + "..." if len(comments) > 30 else comments
        
        option = f"{date} | {category} | {score}/10 | {comments_preview}"
        options.append(option)
    
    # Run fzf
    try:
        process = subprocess.run(
            ["fzf", "--height=40%", "--layout=reverse", "--prompt=Select evaluation: "],
            input="\n".join(options),
            text=True,
            capture_output=True
        )
        
        if process.returncode == 0:
            selected_line = process.stdout.strip()
            # Find the corresponding evaluation
            for i, option in enumerate(options):
                if option == selected_line:
                    return evaluations[i]
        
        return None
    except Exception as e:
        typer.echo(f"Error running fzf: {e}", err=True)
        return None

def parse_date_range(range_str: str) -> tuple[str, str]:
    """Parse date range string in format YYYY-MM-DD:YYYY-MM-DD"""
    if ':' not in range_str:
        # Single date
        return range_str, range_str
    
    parts = range_str.split(':', 1)
    start_date = parts[0].strip()
    end_date = parts[1].strip()
    
    # Validate date format
    try:
        datetime.strptime(start_date, '%Y-%m-%d')
        datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        typer.echo("Error: Date range must be in YYYY-MM-DD:YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)
    
    return start_date, end_date

def filter_evaluations_by_date_range(evaluations: List[dict], start_date: str, end_date: str) -> List[dict]:
    """Filter evaluations by date range"""
    filtered_evaluations = []
    for eval_entry in evaluations:
        entry_date = eval_entry.get('date', '')
        if start_date <= entry_date <= end_date:
            filtered_evaluations.append(eval_entry)
    return filtered_evaluations

def search_evaluations_by_text(evaluations: List[dict], search_text: str) -> List[dict]:
    """Search evaluations by category or comments"""
    search_lower = search_text.lower()
    filtered_evaluations = []
    
    for eval_entry in evaluations:
        # Search in category
        category = eval_entry.get('category', '').lower()
        if search_lower in category:
            filtered_evaluations.append(eval_entry)
            continue
        
        # Search in comments
        comments = eval_entry.get('comments', '').lower()
        if search_lower in comments:
            filtered_evaluations.append(eval_entry)
            continue
    
    return filtered_evaluations

def generate_report(evaluations: List[dict]) -> str:
    """Generate a summary report of evaluations"""
    if not evaluations:
        return "No evaluations found."
    
    # Group by category
    by_category = defaultdict(list)
    for eval_entry in evaluations:
        category = eval_entry.get('category', 'Unknown')
        by_category[category].append(eval_entry)
    
    report = []
    report.append("# Self-Evaluation Report")
    report.append("")
    
    # Overall statistics
    all_scores = [eval_entry.get('score', 0) for eval_entry in evaluations]
    report.append(f"**Total evaluations:** {len(evaluations)}")
    report.append(f"**Overall average:** {statistics.mean(all_scores):.2f}")
    report.append(f"**Overall median:** {statistics.median(all_scores):.2f}")
    report.append("")
    
    # Category statistics
    report.append("## By Category")
    report.append("")
    
    for category, category_evals in sorted(by_category.items()):
        scores = [eval_entry.get('score', 0) for eval_entry in category_evals]
        dates = [eval_entry.get('date', '') for eval_entry in category_evals]
        
        report.append(f"### {category}")
        report.append(f"- **Count:** {len(category_evals)}")
        report.append(f"- **Average:** {statistics.mean(scores):.2f}")
        report.append(f"- **Median:** {statistics.median(scores):.2f}")
        report.append(f"- **Min:** {min(scores)}")
        report.append(f"- **Max:** {max(scores)}")
        report.append(f"- **Date range:** {min(dates)} to {max(dates)}")
        report.append("")
    
    # Recent entries
    recent_evals = sorted(evaluations, key=lambda x: x.get('date', ''), reverse=True)[:10]
    report.append("## Recent Evaluations")
    report.append("")
    
    for eval_entry in recent_evals:
        date = eval_entry.get('date', '')
        category = eval_entry.get('category', '')
        score = eval_entry.get('score', 0)
        comments = eval_entry.get('comments', '')
        
        report.append(f"**{date}** | {category} | {score}/10")
        if comments:
            report.append(f"  *{comments}*")
        report.append("")
    
    return "\n".join(report)

def add_evaluation(
    category: Annotated[str, typer.Option("--category", help="Category of the evaluation (e.g., 'productivity', 'health')")],
    score: Annotated[int, typer.Option("--score", help="Numeric score for the evaluation (1-10)")],
    date: Annotated[Optional[str], typer.Option("--date", help="Date of the evaluation in YYYY-MM-DD format (defaults to today)")] = None,
    comments: Annotated[Optional[str], typer.Option("--comments", help="Optional free-text comments for the evaluation")] = None,
):
    """Add a new evaluation entry"""
    if not category:
        typer.echo("Error: Category is required", err=True)
        raise typer.Exit(code=1)
    
    if score < 1 or score > 10:
        typer.echo("Error: Score must be between 1 and 10", err=True)
        raise typer.Exit(code=1)
    
    # Set default date if not provided
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)
    
    # Set default comments
    if comments is None:
        comments = ""
    
    # Add or update evaluation
    was_updated = add_or_update_evaluation(date, category, score, comments)
    
    if was_updated:
        typer.echo(f"✅ Evaluation updated: {category} on {date} (score: {score})")
    else:
        typer.echo(f"✅ Evaluation added: {category} on {date} (score: {score})")

def list_evaluations(
    limit: Annotated[Optional[int], typer.Option("--limit", "-l", help="Limit the number of evaluations to display")] = None,
    category: Annotated[Optional[str], typer.Option("--category", help="Filter by category")] = None,
    date_range: Annotated[Optional[str], typer.Option("--range", help="Filter by date range (YYYY-MM-DD:YYYY-MM-DD)")] = None,
    no_interactive: Annotated[bool, typer.Option("--no-interactive", help="Disable interactive selection even if fzf is available")] = False,
):
    """List all evaluations"""
    evaluations = get_all_evaluations()
    
    if not evaluations:
        typer.echo("No evaluations found.")
        return
    
    # Filter by category if specified
    if category:
        evaluations = [e for e in evaluations if e.get('category', '').lower() == category.lower()]
    
    # Filter by date range if specified
    if date_range:
        start_date, end_date = parse_date_range(date_range)
        evaluations = filter_evaluations_by_date_range(evaluations, start_date, end_date)
    
    # Apply limit if specified
    if limit:
        evaluations = evaluations[:limit]
    
    # Use fzf if available for interactive selection (unless disabled)
    if not no_interactive and is_fzf_available():
        selected_eval = select_evaluation_with_fzf(evaluations)
        if selected_eval:
            # Display selected evaluation details
            date = selected_eval.get('date', '')
            category = selected_eval.get('category', '')
            score = selected_eval.get('score', 0)
            comments = selected_eval.get('comments', '')
            
            typer.echo(f"Date: {date}")
            typer.echo(f"Category: {category}")
            typer.echo(f"Score: {score}/10")
            if comments:
                typer.echo(f"Comments: {comments}")
        return
    
    # Display evaluations
    for eval_entry in evaluations:
        date = eval_entry.get('date', '')
        category = eval_entry.get('category', '')
        score = eval_entry.get('score', 0)
        comments = eval_entry.get('comments', '')
        
        # Truncate comments for display
        comments_preview = comments[:40] + "..." if len(comments) > 40 else comments
        
        typer.echo(f"{date} | {category} | {score}/10 | {comments_preview}")

def edit_evaluation(
    category: Annotated[str, typer.Option("--category", help="Category of the evaluation to edit")],
    date: Annotated[Optional[str], typer.Option("--date", help="Date of the evaluation to edit (defaults to today)")] = None,
    score: Annotated[Optional[int], typer.Option("--score", help="New score for the evaluation (1-10)")] = None,
    comments: Annotated[Optional[str], typer.Option("--comments", help="New comments for the evaluation")] = None,
):
    """Edit an existing evaluation"""
    if not category:
        typer.echo("Error: Category is required", err=True)
        raise typer.Exit(code=1)
    
    # Set default date if not provided
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)
    
    # Find existing evaluation
    existing_eval = find_evaluation_by_date_and_category(date, category)
    if not existing_eval:
        typer.echo(f"Evaluation not found: {category} on {date}")
        return
    
    # Use existing values if not provided
    new_score = score if score is not None else existing_eval.get('score', 0)
    new_comments = comments if comments is not None else existing_eval.get('comments', '')
    
    # Validate score
    if new_score < 1 or new_score > 10:
        typer.echo("Error: Score must be between 1 and 10", err=True)
        raise typer.Exit(code=1)
    
    # Update evaluation
    add_or_update_evaluation(date, category, new_score, new_comments)
    
    typer.echo(f"✅ Evaluation updated: {category} on {date} (score: {new_score})")

def delete_evaluation(
    category: Annotated[str, typer.Option("--category", help="Category of the evaluation to delete")],
    date: Annotated[Optional[str], typer.Option("--date", help="Date of the evaluation to delete (defaults to today)")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help="Force deletion without confirmation")] = False,
):
    """Delete an evaluation"""
    if not category:
        typer.echo("Error: Category is required", err=True)
        raise typer.Exit(code=1)
    
    # Set default date if not provided
    if not date:
        date = datetime.now().strftime('%Y-%m-%d')
    
    # Validate date format
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        typer.echo("Error: Date must be in YYYY-MM-DD format", err=True)
        raise typer.Exit(code=1)
    
    # Find existing evaluation
    existing_eval = find_evaluation_by_date_and_category(date, category)
    if not existing_eval:
        typer.echo(f"Evaluation not found: {category} on {date}")
        return
    
    # Confirm deletion
    if not force:
        score = existing_eval.get('score', 0)
        if not typer.confirm(f"Are you sure you want to delete evaluation '{category}' on {date} (score: {score})?"):
            typer.echo("Deletion cancelled.")
            return
    
    # Delete evaluation
    if remove_evaluation(date, category):
        typer.echo(f"✅ Evaluation deleted: {category} on {date}")
    else:
        typer.echo(f"Error deleting evaluation: {category} on {date}")

def generate_evaluation_report(
    date_range: Annotated[Optional[str], typer.Option("--range", help="Date range for the report (YYYY-MM-DD:YYYY-MM-DD)")] = None,
    category: Annotated[Optional[str], typer.Option("--category", help="Filter report by category")] = None,
):
    """Generate a summary report of evaluations"""
    evaluations = get_all_evaluations()
    
    if not evaluations:
        typer.echo("No evaluations found.")
        return
    
    # Filter by date range if specified
    if date_range:
        start_date, end_date = parse_date_range(date_range)
        evaluations = filter_evaluations_by_date_range(evaluations, start_date, end_date)
    else:
        # Default to past year
        one_year_ago = datetime.now() - timedelta(days=365)
        start_date = one_year_ago.strftime('%Y-%m-%d')
        end_date = datetime.now().strftime('%Y-%m-%d')
        evaluations = filter_evaluations_by_date_range(evaluations, start_date, end_date)
    
    # Filter by category if specified
    if category:
        evaluations = [e for e in evaluations if e.get('category', '').lower() == category.lower()]
    
    if not evaluations:
        typer.echo("No evaluations found for the specified criteria.")
        return
    
    # Generate and display report
    report = generate_report(evaluations)
    typer.echo(report)

# Create the Typer app for eval commands
eval_app = typer.Typer(name="eval", help="Manage self-evaluation entries")

eval_app.command("add")(add_evaluation)
eval_app.command("list")(list_evaluations)
eval_app.command("edit")(edit_evaluation)
eval_app.command("delete")(delete_evaluation)
eval_app.command("report")(generate_evaluation_report)

if __name__ == "__main__":
    eval_app()
