# ติดตั้งงานและสกิลบนเครื่องใหม่

## 1. ติดตั้งโปรแกรม

- Git
- Claude desktop app แล้วล็อกอินบัญชีเดิม
- Blender และ Blender MCP add-on

## 2. โหลดโปรเจค

เปิด PowerShell แล้วรันทีละบรรทัด โดยเปลี่ยน `<REPO_URL>` เป็นลิงก์ repo ส่วนตัว

```powershell
New-Item -ItemType Directory -Force D:\JEFF\JeffCompany
git clone --branch machine-transfer <REPO_URL> D:\JEFF\JeffCompany\Blender
```

ควรใช้ path เดิม เพราะชื่อโฟลเดอร์ memory ผูกกับ path นี้

## 3. ติดตั้งสกิลและ memory

```powershell
cd D:\JEFF\JeffCompany\Blender
.\machine-transfer\install.ps1
```

ถ้า Windows ไม่ให้รันสคริปต์ ใช้คำสั่งนี้แทน

```powershell
powershell -ExecutionPolicy Bypass -File .\machine-transfer\install.ps1
```

## 4. ตรวจผล

ปิดแล้วเปิด Claude ใหม่ เปิดโฟลเดอร์ `D:\JEFF\JeffCompany\Blender` แล้วดูว่ามีสกิล เช่น `voxel-style` และ `voxel-boss`

## สิ่งที่ไม่ได้ย้ายมา

- การล็อกอิน: Claude, GitHub และ NotebookLM ต้องล็อกอินใหม่
- ประวัติแชตเก่า
- สกิลในโฟลเดอร์ `synced`: มาจากบัญชี Claude
