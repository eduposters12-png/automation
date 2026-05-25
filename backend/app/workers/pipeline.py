from backend.app.models.job import Job, JobStatus


def mark_job_as_queued(job: Job) -> Job:
    """Placeholder boundary for external AI/Etsy workers."""
    job.status = JobStatus.PENDING
    return job
