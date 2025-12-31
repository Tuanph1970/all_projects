# Vietnamese Math Tutor - Example Interactions

This document provides example interactions demonstrating the expected behavior of the Vietnamese Math Tutor system.

---

## Vietnamese Interaction Example

### User Input
```
Tim dao ham cua ham so f(x) = x^3 - 3x^2 + 2x - 1
```

### Expected Response
```
**Phan tich de bai:**
Cho ham so f(x) = x^3 - 3x^2 + 2x - 1
Can tim dao ham f'(x).

**Buoc 1: Ap dung cong thuc dao ham co ban**
- Dao ham cua x^n la n*x^(n-1)
- Dao ham cua hang so bang 0

**Buoc 2: Tinh dao ham tung hang tu**
- (x^3)' = 3x^2
- (-3x^2)' = -6x
- (2x)' = 2
- (-1)' = 0

**Buoc 3: Tong hop ket qua**
f'(x) = 3x^2 - 6x + 2

**Kiem tra:** Thay x = 1: f'(1) = 3(1)^2 - 6(1) + 2 = 3 - 6 + 2 = -1

**Dap an:** f'(x) = 3x^2 - 6x + 2
```

---

## English Interaction Example

### User Input
```
Find the integral of f(x) = 2x + 3
```

### Expected Response
```
**Problem Analysis:**
Given function f(x) = 2x + 3
Find the indefinite integral (antiderivative).

**Step 1: Apply basic integration rules**
- Integral of x^n is x^(n+1)/(n+1)
- Integral of a constant k is kx

**Step 2: Integrate each term**
- Integral of 2x = 2 * x^2/2 = x^2
- Integral of 3 = 3x

**Step 3: Combine results**
F(x) = x^2 + 3x + C

**Verification:** F'(x) = 2x + 3 = f(x) (verified)

**Answer:** The integral of f(x) = 2x + 3 is F(x) = x^2 + 3x + C
```

---

## Combinatorics Example (Vietnamese)

### User Input
```
Tinh so cach chon 3 hoc sinh tu 10 hoc sinh de tham gia cuoc thi
```

### Expected Response
```
**Phan tich de bai:**
- Chon 3 hoc sinh tu 10 hoc sinh
- Thu tu khong quan trong (chi can chon, khong phan biet vi tri)
- Day la bai toan to hop

**Buoc 1: Xac dinh cong thuc**
So cach chon k phan tu tu n phan tu (khong quan tam thu tu):
C(n,k) = n! / (k! * (n-k)!)

**Buoc 2: Thay so**
C(10,3) = 10! / (3! * 7!)

**Buoc 3: Tinh toan**
C(10,3) = (10 * 9 * 8) / (3 * 2 * 1)
C(10,3) = 720 / 6
C(10,3) = 120

**Dap an:** Co 120 cach chon 3 hoc sinh tu 10 hoc sinh.
```

---

## Geometry Example (Coordinate Geometry)

### User Input
```
Tim phuong trinh mat phang di qua 3 diem A(1,0,0), B(0,2,0), C(0,0,3)
```

### Expected Response
```
**Phan tich de bai:**
Tim phuong trinh mat phang (P) di qua 3 diem:
- A(1, 0, 0)
- B(0, 2, 0)
- C(0, 0, 3)

**Buoc 1: Tim hai vecto chi phuong**
AB = B - A = (-1, 2, 0)
AC = C - A = (-1, 0, 3)

**Buoc 2: Tim vecto phap tuyen (tich co huong)**
n = AB x AC = |i   j   k |
               |-1  2   0 |
               |-1  0   3 |

n = i(2*3 - 0*0) - j((-1)*3 - 0*(-1)) + k((-1)*0 - 2*(-1))
n = (6, 3, 2)

**Buoc 3: Lap phuong trinh mat phang**
Phuong trinh mat phang qua A(1,0,0) voi vecto phap tuyen n = (6,3,2):
6(x-1) + 3(y-0) + 2(z-0) = 0
6x - 6 + 3y + 2z = 0
6x + 3y + 2z = 6

**Kiem tra:**
- Thay A(1,0,0): 6(1) + 3(0) + 2(0) = 6 (OK)
- Thay B(0,2,0): 6(0) + 3(2) + 2(0) = 6 (OK)
- Thay C(0,0,3): 6(0) + 3(0) + 2(3) = 6 (OK)

**Dap an:** Phuong trinh mat phang: 6x + 3y + 2z = 6
Hoac dang: x/1 + y/2 + z/3 = 1
```

---

## Probability Example

### User Input
```
Tu mot hop co 5 bi do va 3 bi xanh, lay ngau nhien 2 bi. Tinh xac suat de ca 2 bi deu do.
```

### Expected Response
```
**Phan tich de bai:**
- Hop co: 5 bi do + 3 bi xanh = 8 bi
- Lay ngau nhien 2 bi
- Tim xac suat ca 2 bi deu do

**Buoc 1: Tinh so cach chon 2 bi bat ky tu 8 bi**
So phan tu khong gian mau:
n(Omega) = C(8,2) = 8!/(2!*6!) = 28

**Buoc 2: Tinh so cach chon 2 bi do tu 5 bi do**
So ket qua thuan loi (bien co A: "ca 2 bi deu do"):
n(A) = C(5,2) = 5!/(2!*3!) = 10

**Buoc 3: Tinh xac suat**
P(A) = n(A)/n(Omega) = 10/28 = 5/14

**Dap an:** Xac suat de ca 2 bi deu do la P = 5/14 (xap xi 0.357 hay 35.7%)
```

---

## Function Analysis Example (Grade 12)

### User Input
```
Khao sat su bien thien va ve do thi ham so y = x^3 - 3x + 2
```

### Expected Response
```
**Phan tich de bai:**
Khao sat ham so y = f(x) = x^3 - 3x + 2

**Buoc 1: Tap xac dinh**
D = R (ham da thuc xac dinh tren toan bo tap so thuc)

**Buoc 2: Su bien thien**
a) Dao ham: y' = 3x^2 - 3 = 3(x^2 - 1) = 3(x-1)(x+1)
b) y' = 0 khi x = -1 hoac x = 1
c) Bang xet dau:
   - x < -1: y' > 0 (ham dong bien)
   - -1 < x < 1: y' < 0 (ham nghich bien)
   - x > 1: y' > 0 (ham dong bien)

**Buoc 3: Cuc tri**
- Cuc dai tai x = -1: y(-1) = (-1)^3 - 3(-1) + 2 = -1 + 3 + 2 = 4
  Diem cuc dai: (-1, 4)
- Cuc tieu tai x = 1: y(1) = 1 - 3 + 2 = 0
  Diem cuc tieu: (1, 0)

**Buoc 4: Gioi han**
- lim(x->+inf) y = +inf
- lim(x->-inf) y = -inf

**Buoc 5: Bang bien thien**
x     | -inf     -1      1      +inf
y'    |    +      0   -   0   +
y     | -inf /* 4  \  0  /* +inf
             CD      CT

**Buoc 6: Diem dac biet**
- Giao Oy: x = 0 => y = 2, diem (0, 2)
- Giao Ox: y = 0 => x^3 - 3x + 2 = 0
  => (x-1)(x^2+x-2) = 0
  => (x-1)(x-1)(x+2) = 0
  => x = 1 (nghiem kep) hoac x = -2
  Diem (-2, 0) va (1, 0)

**Do thi:** Ham so bac 3 voi cuc dai tai (-1, 4) va cuc tieu tai (1, 0)
```

---

## Statistics Example

### User Input
```
Cho day so lieu: 5, 7, 8, 6, 9, 7, 8, 5, 7, 8. Tinh trung binh va phuong sai.
```

### Expected Response
```
**Phan tich de bai:**
Day so lieu: 5, 7, 8, 6, 9, 7, 8, 5, 7, 8
Co n = 10 gia tri

**Buoc 1: Tinh trung binh (mean)**
x_bar = (5 + 7 + 8 + 6 + 9 + 7 + 8 + 5 + 7 + 8) / 10
x_bar = 70 / 10 = 7

**Buoc 2: Tinh phuong sai (variance)**
Cong thuc: s^2 = (1/n) * Sum[(xi - x_bar)^2]

Tinh tung do lech binh phuong:
- (5-7)^2 = 4
- (7-7)^2 = 0
- (8-7)^2 = 1
- (6-7)^2 = 1
- (9-7)^2 = 4
- (7-7)^2 = 0
- (8-7)^2 = 1
- (5-7)^2 = 4
- (7-7)^2 = 0
- (8-7)^2 = 1

Tong: 4 + 0 + 1 + 1 + 4 + 0 + 1 + 4 + 0 + 1 = 16

s^2 = 16/10 = 1.6

**Buoc 3: Tinh do lech chuan (standard deviation)**
s = sqrt(1.6) ≈ 1.265

**Dap an:**
- Trung binh: x_bar = 7
- Phuong sai: s^2 = 1.6
- Do lech chuan: s ≈ 1.265
```

---

## Design Document Summary

The complete system design is available in `DESIGN.md` with:
- Full system architecture
- Component specifications
- API contracts
- Implementation phases
- Risk analysis

**Ready for implementation upon approval.**
