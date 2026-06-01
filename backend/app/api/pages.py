"""
Research Agent — Pages Blueprint

Serves HTML templates for the frontend.
"""

from flask import Blueprint, render_template

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
def index():
    """Landing / Dashboard page."""
    return render_template('index.html')


@pages_bp.route('/login')
def login_page():
    """Login page."""
    return render_template('login.html')


@pages_bp.route('/register')
def register_page():
    """Register page."""
    return render_template('register.html')


@pages_bp.route('/dashboard')
def dashboard_page():
    """Dashboard page (after login)."""
    return render_template('dashboard.html')


@pages_bp.route('/upload')
def upload_page():
    """Paper upload page."""
    return render_template('upload.html')


@pages_bp.route('/papers')
def papers_page():
    """Paper library page."""
    return render_template('papers.html')


@pages_bp.route('/papers/<int:paper_id>')
def paper_detail_page(paper_id):
    """Single paper detail page."""
    return render_template('paper_detail.html', paper_id=paper_id)





@pages_bp.route('/research')
def research_page():
    """AI Research Assistant page (multi-agent)."""
    return render_template('research.html')


@pages_bp.route('/evaluation')
def evaluation_page():
    """System evaluation dashboard page."""
    return render_template('evaluation.html')
