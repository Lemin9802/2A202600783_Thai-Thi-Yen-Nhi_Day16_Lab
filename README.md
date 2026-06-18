# Day 16 - Track 2 Assignment

## Cloud Infrastructure for AI - CPU Fallback Deployment

Repo này là bài lab Day 16 cho chủ đề Cloud Infrastructure for AI. Mục tiêu ban đầu của lab là triển khai một AI serving environment trên Google Cloud bằng Terraform Infrastructure as Code, sử dụng GPU VM để chạy inference endpoint. Tuy nhiên, trong quá trình thực hiện, project GCP không có đủ global GPU quota, nên bài lab được hoàn thành theo hướng CPU fallback với VM e2-standard-8 và LightGBM benchmark.

---

## 1. Lab Objective

Bài lab tập trung vào các nội dung chính:

- Provision cloud infrastructure bằng Terraform IaC.
- Thiết lập VPC, private subnet, firewall rules, Cloud NAT và Load Balancer.
- Deploy compute instance trên Google Cloud.
- Truy cập VM thông qua IAP SSH.
- Chạy Machine Learning benchmark workload trên cloud VM.
- Thu thập benchmark metrics, billing evidence và cleanup evidence.
- Thực hiện terraform destroy để tránh phát sinh chi phí sau lab.

---

## 2. Cloud Environment

| Item | Value |
|---|---|
| Cloud Provider | Google Cloud Platform |
| Project ID | forward-alchemy-442913-f9 |
| Region | us-central1 |
| Zone | us-central1-f |
| Deployment Method | Terraform |
| Compute Instance | ai-gpu-node |
| Final Machine Type | e2-standard-8 |
| Operating System | Debian GNU/Linux 12 |
| CPU | 8 vCPU |
| GPU | Not used - CPU fallback |
| Load Balancer IP | 8.233.165.194 |
| API Endpoint Output | http://8.233.165.194/v1 |

---

## 3. Reason for CPU Fallback

Lab gốc yêu cầu GPU VM. Tuy nhiên, project GCP có global GPU quota bằng 0.

Quota evidence:

| Metric | Limit | Usage |
|---|---:|---:|
| CPUS_ALL_REGIONS | 32.0 | 0.0 |
| GPUS_ALL_REGIONS | 0.0 | 0.0 |

Vì GPUS_ALL_REGIONS = 0.0, GPU VM không thể được tạo thành công. Do đó, bài lab được chuyển sang CPU fallback để vẫn đảm bảo workflow chính:

Terraform IaC -> Cloud VM -> ML workload -> Benchmark metrics -> Billing evidence -> Cleanup

Screenshot liên quan:

- screenshots/00_gpu_quota_zero_reason_for_cpu_fallback.png

---

## 4. Infrastructure Created by Terraform

Terraform đã tạo các cloud resources sau:

- Custom VPC: ai-vpc
- Private subnet: ai-private-subnet
- Cloud Router: ai-router
- Cloud NAT: ai-nat
- Firewall rule for IAP SSH
- Firewall rule for Load Balancer health check
- Service Account for compute node
- VM instance: ai-gpu-node
- Instance group
- HTTP Load Balancer
- Backend service
- URL map
- HTTP proxy
- Global forwarding rule

Terraform apply evidence:

- screenshots/01_terraform_apply_success.png

Apply result:

| Output | Value |
|---|---|
| api_endpoint | http://8.233.165.194/v1 |
| gpu_node_name | ai-gpu-node |
| gpu_node_zone | us-central1-f |
| iap_ssh_command | gcloud compute ssh ai-gpu-node --zone=us-central1-f --tunnel-through-iap |
| load_balancer_ip | 8.233.165.194 |

---

## 5. VM Verification

VM được truy cập thông qua Google Cloud IAP SSH.

Verification commands:

- hostname
- cat /etc/os-release | head
- nproc
- curl Metadata server để kiểm tra machine-type

Kết quả:

| Check | Result |
|---|---|
| Hostname | ai-gpu-node |
| OS | Debian GNU/Linux 12 |
| CPU cores | 8 |
| Machine type | e2-standard-8 |

Screenshot:

- screenshots/02_vm_machine_check_e2_standard_8.png

---

## 6. ML Benchmark

Vì không có GPU quota, workload được chuyển sang LightGBM CPU benchmark. Benchmark mô phỏng bài toán fraud detection với synthetic fraud-like dataset.

Files:

- evidence/benchmark.py
- evidence/benchmark_result.json

Benchmark command:

- python benchmark.py

Dataset summary:

| Item | Value |
|---|---:|
| Dataset source | synthetic_fraud_like |
| Rows | 284,807 |
| Features | 30 |
| Positive class count | 1,961 |
| Positive class ratio | 0.006885 |

Benchmark results:

| Metric | Value |
|---|---:|
| Load/generation time | 0.4636 sec |
| Training time | 1.1412 sec |
| Best iteration | 12 |
| AUC-ROC | 0.6529 |
| Accuracy | 0.902303 |
| F1-score | 0.04953 |
| Precision | 0.026542 |
| Recall | 0.369898 |
| Inference latency - 1 row | 2.167486 ms |
| Inference throughput - 1000 rows | 730157.25 rows/sec |

Screenshot:

- screenshots/03_lightgbm_benchmark_result.png

---

## 7. Billing Evidence

Billing Reports và Cost Table đã được kiểm tra sau khi lab hoàn thành.

Google Cloud Billing hiển thị chi phí hiện tại là 0 VND tại thời điểm chụp. Trang Billing cũng hiển thị thông báo rằng cost có thể mất vài giờ hoặc hơn 24 giờ để cập nhật.

Screenshots:

- screenshots/04_billing_report_initial_0vnd_delay.png
- screenshots/05_billing_cost_table_initial_0vnd.png

Billing note:

Billing was checked immediately after completing the lab. Google Cloud displayed current cost as 0 VND and showed that costs may take a few hours or longer than 24 hours to appear.

Estimated active cost drivers trong thời gian lab chạy:

- e2-standard-8 Compute Engine VM
- 100GB persistent boot disk
- Cloud NAT
- External HTTP Load Balancer
- Global forwarding rule

---

## 8. Cleanup

Sau khi thu thập evidence, toàn bộ resources đã được xóa bằng Terraform.

Command:

- terraform destroy

Kết quả:

- Destroy complete! Resources: 16 destroyed.

Sau cleanup, kiểm tra VM:

- gcloud compute instances list --project=forward-alchemy-442913-f9

Kết quả:

- Listed 0 items.

Screenshot:

- screenshots/06_terraform_destroy_complete.png

Cleanup evidence files:

- evidence/after_destroy_instances.txt
- evidence/after_destroy_forwarding_rules.txt
- evidence/terraform_state_after_destroy.txt

---

## 9. Repository Structure

Expected submission structure:

- README.md
- .gitignore
- terraform-gcp/
  - main.tf
  - variables.tf
  - providers.tf
  - outputs.tf
  - user_data.sh
- evidence/
  - benchmark.py
  - benchmark_result.json
  - terraform_outputs.txt
  - gcp_instances.txt
  - gcp_forwarding_rules.txt
  - after_destroy_instances.txt
  - after_destroy_forwarding_rules.txt
  - terraform_state_after_destroy.txt
- screenshots/
  - 00_gpu_quota_zero_reason_for_cpu_fallback.png
  - 01_terraform_apply_success.png
  - 02_vm_machine_check_e2_standard_8.png
  - 03_lightgbm_benchmark_result.png
  - 04_billing_report_initial_0vnd_delay.png
  - 05_billing_cost_table_initial_0vnd.png
  - 06_terraform_destroy_complete.png

---

## 10. Important Notes

- Terraform state files, local plan files, .terraform/, secrets and backup files are excluded by .gitignore.
- GPU path was not used because GPUS_ALL_REGIONS quota was 0.0.
- CPU fallback still demonstrates the full cloud infrastructure workflow.
- All cloud resources were destroyed after the lab to avoid unnecessary cost.
- Billing may update later because Google Cloud cost reporting is not always real-time.

---

## 11. Final Submission Checklist

- [x] GPU quota screenshot showing CPU fallback reason
- [x] Terraform apply screenshot
- [x] VM verification screenshot
- [x] LightGBM benchmark screenshot
- [x] benchmark.py
- [x] benchmark_result.json
- [x] Billing Reports screenshot
- [x] Cost Table screenshot
- [x] Terraform destroy screenshot
- [x] Terraform source files
- [x] Evidence logs

