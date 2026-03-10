# Database Migration Considerations (RDS Alternatives)

> **Date:** 2026-03-09
> **Context:** The user asked if we can create the system without using AWS RDS, as it is the biggest cost factor in the equation during the 6-month testing phase.

## The Problem
AWS RDS (even when paused) still incurs storage costs, and keeping it requires a NAT Gateway and Bastion Host for secure access, which adds up to ~$40-50/month even in cost-conscious mode. During a testing phase with a small user base, this 24/7 infrastructure is unnecessary.

## Available Alternatives

### Option 1: Migrate to a Free-Tier Cloud PostgreSQL (Recommended)
Providers like **Neon.tech** or **Supabase** offer generous free tiers for managed Serverless PostgreSQL databases.
- **Cost:** $0/month.
- **Effort:** Very Low. Since they provide standard PostgreSQL databases, no Python or SQL code needs to be modified.
- **Migration Path:** Export data from RDS -> Import to Neon/Supabase -> Update `DB_HOST`, `DB_USER`, `DB_PASSWORD` environment variables -> Destroy RDS.
- **Note:** Free tiers usually limit DB size to 500MB. The current 1.7M rows of Nifty 500 data take up ~200–300MB, fitting perfectly.

### Option 2: Run PostgreSQL Locally
Run PostgreSQL via Docker or native WSL on the development laptop.
- **Cost:** $0/month.
- **Effort:** Low. Just install Postgres, restore data locally, and point scripts to `localhost:5432`.
- **Drawback:** The laptop becomes a single point of failure. It makes deploying a 24/7 cloud API harder later without migrating back to a cloud DB.

### Option 3: Refactor to SQLite
Replace PostgreSQL entirely with a serverless file-based SQLite database (`mri_data.db`).
- **Cost:** $0/month.
- **Effort:** Medium. Requires modifying Python and SQL code, as SQLite handles dates, UUIDs, and concurrent writes differently.

## Does migrating away from RDS ruin the "AWS Project" portfolio value?
**No.** Modern architectures frequently mix "best-of-breed" managed services. Many top-tier startups use AWS for compute (ECS), storage (S3), routing (CloudFront/ALB), and DNS while outsourcing the database to specialized DaaS providers like Neon.

Furthermore, the AWS architecture value is retained in the Terraform code. By commenting out the RDS module (or using a feature toggle like `create_rds = false`), the repository still proves the ability to:
1. Provision secure, private RDS instances with subnet groups.
2. Build AWS Bastion Hosts and SSM Tunnels.
3. Make pragmatic, business-savvy engineering decisions to optimize costs during beta testing phases.

## Next Steps (To be decided)
If taking Option 1, the immediate next step is creating the target database, dumping the current `mri_db` from RDS, restoring it to the new provider, updating the `secretsmanager` credentials, and applying a Terraform update to destroy the AWS RDS instance and Bastion EC2.
