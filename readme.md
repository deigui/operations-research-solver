



# 说明文档

# 源码运行准备工作

**完整步骤：在没有Python环境的电脑上运行**

------

**第一步：下载Python**

1. 打开浏览器，访问 `https://www.python.org/downloads/`
2. 点击黄色大按钮 **"Download Python 3.11.x"**
3. 下载完成后双击安装包（文件名类似 `python-3.11.9-amd64.exe`）

------

**第二步：安装Python（关键！）**

安装界面出现后：

- ✅ 勾选底部的 **"Add python.exe to PATH"**（非常重要，默认不勾）
- 然后点 **"Install Now"**
- 等待安装完成，点 **"Close"**

------

**第三步：打开命令行**

- 按 `Win + R`，输入 `cmd`，回车
- 或者在开始菜单搜索 **"命令提示符"** 打开

------

**第四步：切换到文件所在目录**

假设文件放在桌面的"求解工具"文件夹里：

```
cd C:\Users\你的用户名\Desktop\求解工具
```

更简单的方法：

1. 打开存放 `main.py` 的项目文件夹
2. 在地址栏输入 `cmd` 回车，直接在当前目录打开命令行

------

**第五步：安装依赖库**

```
pip install scipy matplotlib pulp
```

等待安装完成（需要联网，约1-2分钟）

------

**第六步：运行程序**

```
python main.py
```

程序窗口会弹出，之后每次运行只需要重复第三、四、六步。

------

**常见问题：**

- **提示"pip不是内部命令"** → 第二步没有勾选"Add to PATH"，重新安装勾上
- **提示"No module named scipy"** → 第五步没成功，重新运行 `pip install scipy matplotlib pulp`
- **窗口一闪而过** → 说明程序有错误，改用 `python main.py` 在cmd里运行查看错误信息

# 打包成exe（一劳永逸）

在**已有Python环境的电脑**上运行一次：

```
pip install pyinstaller
pyinstaller --onefile --windowed --name "运筹学模型求解工具" --paths src main.py
```

生成的 `dist\运筹学模型求解工具.exe` 发给任何人，双击直接用，不需要Python。

# 测试数据

## 决策分析-默认3*3表格 可根据拷贝的数据矩阵自动扩展行列
### 最大最小准则

12	14	13
15	17	14
13	15	18
10	16	12

![image-20260728155954649](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728155954649.png)

### 最大最大准则

12	14	13
15	17	14
13	15	18
10	16	12

![image-20260728160027062](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160027062.png)

### 乐观系数准则[系数可调]

12	14	13
15	17	14
13	15	18
10	16	12

![image-20260728160128103](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160128103.png)

### 等可能性准则-可特殊使用
12	14	13  11
15	17	14  12
13	15	18  12
10	16	12  11

![image-20260728160238031](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160238031.png)

### 后悔值准则

12	14	13  11
15	17	14  12
13	15	18  12
10	16	12  11

![image-20260728160400823](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160400823.png)

### 期望值准则

0.2	0.5	0.3 
12	14	13 
15	17	14
13	15	18
10	16	12

![image-20260728160305827](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160305827.png)

0.2	0.5	0.2 0.1
12	14	13  12
15	17	14  11
13	15	18  10
10	16	12  1

### 全情报准则

8	2	5
4	9	3
1	6	7

![image-20260728160815429](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160815429.png)

### 部分情报准则

8	2	5
4	9	3
1	6	7

![image-20260728160942908](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728160942908.png)

### 效用值准则

0.90  0.20  0.60
0.50  0.95  0.40
0.10  0.70  0.75

![image-20260728161855247](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728161855247.png)

## 线性规划



max  Z = 15x1   + 10x2   + 7x3   + 13x4   + 9x5

s.t.
  5x1   + 10x2   + 7x3  ≤  8000
  6x1   + 4x2   + 8x3   + 6x4   + 4x5  ≤  12000
  3x1   + 2x2   + 2x3   + 3x4   + 2x5  ≤  10000

  x1 >= 0
  x2 >= 0
  x3 >= 0
  x4 >= 0
  x5 >= 0

### 线性规划问题

max  Z = 15x₁ + 10x₂ + 7x₃ + 13x₄ + 9x₅

s.t.
  5x₁ + 10x₂ + 7x₃ >= 8000
  6x₁ + 4x₂ + 8x₃ + 6x₄ + 4x₅ <= 12000
  3x₁ + 2x₂ + 2x₃ + 3x₄ + 2x₅ <= 10000

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0



5	10	7		
6	4	8	6	4
3	2	2	3	2

![image-20260728162645539](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728162645539.png)

### 表格式线性规划

max
15 10 7 13 9
5 10 7 0 0 <= 8000
6 4 8 6 4 <= 12000
3 2 2 3 2 <= 10000

![image-20260728163058914](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728163058914.png)

### 连续投资问题

maxz=1.1x₅+1.25x₉+1.40x₁₀+1.55x₁₁

s.t. 
X₁+x₆≤300
-1.1x₁+x₂+x₇+x₁₁≤0
-1.1x₂+x₃-1.25x₆+x₈+x₁₀≤0 
-1.1x₃+x₄-1.25x₇+x₉≤0
-1.1x₄+x₅-1.25x₈≤0
x₆≤50
x₇≤50
x₈≤50
x₉≤50
x₁₀≤100
x₁₁≤150
x≥0

![image-20260728164134007](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728164134007.png)

### 产品自制与外销

max  Z = 15x₁ + 10x₂ + 7x₃ + 13x₄ + 9x₅

s.t.
  5x₁ + 10x₂ + 7x₃ <= 8000
  6x₁ + 4x₂ + 8x₃ + 6x₄ + 4x₅ <= 12000
  3x₁ + 2x₂ + 2x₃ + 3x₄ + 2x₅ <= 10000

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0

![image-20260728164328721](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728164328721.png)

### 合理排班问题

min  Z = 1x₁ + 1x₂ + 1x₃ + 1x₄ + 1x₅ + 1x₆ + 1x₇

s.t.
  1x₁ + 1x₂ + 1x₅ + 1x₆ + 1x₇ >= 24
  1x₁ + 1x₂ + 1x₃ + 1x₆ + 1x₇ >= 25
  1x₁ + 1x₂ + 1x₃ + 1x₄ + 1x₇ >= 20
  1x₁ + 1x₂ + 1x₃ + 1x₄ + 1x₅ >= 28

  1x₃ + 1x₄ + 1x₅ + 1x₆ + 1x₇ >= 34

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0
x₆ >= 0
x₇ >= 0

![image-20260728164446639](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728164446639.png)

### 套装下料

min  Z = 1x₁ + 1x₂ + 1x₃ + 1x₄ + 1x₅ + 1x₆ + 1x₇ + 1x₈

s.t.
  2x₁ + 1x₂ + 1x₃ + 1x₄ >= 100

2x₂ + 1x₃ + 3x₅ + 2x₆ + 1x₇ >= 100
1x₁ + 1x₃ + 3x₄ + 2x₆ + 3x₇ + 4x₈ >= 100

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0
x₆ >= 0
x₇ >= 0
x₈ >= 0

![image-20260728165436864](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728165436864.png)

### 灰色线性规划 --未找见相关例题

## 整数规划

### 纯整数线性规划

max  Z = 50x1 + 100x2

s.t.
  1x1 + 1x2 <= 300
  2x1 + 1x2 <= 400

   1x2 <= 250

  x1 >= 0
  x2 >= 0

![image-20260728165639727](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728165639727.png)

### 0-1整数规划

max  Z = 36x₁ + 54x₂ + 22x₃ + 28x₄ + 35x₅ + 23x₆ + 46x₇ + 59x₈ + 60x₉ + 40x10 + 28x11 + 25x12 + 35x13 + 40x14

s.t.
  80x₁ + 100x₂ + 120x₃ + 110x₄ + 70x₅ + 90x₆ + 80x₇ + 140x₈ + 160x₉ + 150x10 + 130x11 + 60x12 + 80x13 + 70x14 <= 900
  1x₁ + 1x₂ + 1x₃ + 1x₄ <= 3

1x₅ + 1x₆ + 1x₇ >= 2

1x₈ + 1x₉ >= 1

1x10 + 1x11 >= 1

1x12 + 1x13 + 1x14 >= 2

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0
x₆ >= 0
x₇ >= 0
x₈ >= 0
x₉ >= 0
x10 >= 0
x11 >= 0
x12 >= 0
x13 >= 0
x14 >= 0

![image-20260728170245409](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728170245409.png)

### 混合整数规则-投资与选址

min  Z = 8x₁ + 15x₂ + 10x₃ + 12x₄ + 7x₅ + 9x₆ + 18x₇ + 16x₈ + 1x₉ + 11x₁₀ + 12x₁₁ + 8x₁₂ + 19x₁₃ + 4x₁₄ + 15x₁₅ + 370000y₁ + 300000y₂ + 375000y₃ + 500000y₄

s.t.
  1x₁ + 1x₂ + 1x₃ <= 30000

1x₄ + 1x₅ + 1x₆ - -20000y₁ <= 0

1x₇ + 1x₈ + 1x₉ - -40000y₂ <= 0

1x₁₀ + 1x₁₁ + 1x₁₂ - -30000y₃ <= 0

1x₁₃ + 1x₁₄ + 1x₁₅ - -10000y₄ <= 0
1x₁ + 1x₄ + 1x₇ + 1x₁₀ + 1x₁₃ = 30000

1x₂ + 1x₅ + 1x₈ + 1x₁₁ + 1x₁₄ = 20000

1x₃ + 1x₆ + 1x₉ + 1x₁₂ + 1x₁₅ = 20000

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0
x₆ >= 0
x₇ >= 0
x₈ >= 0
x₉ >= 0
x₁₀ >= 0
x₁₁ >= 0
x₁₂ >= 0
x₁₃ >= 0
x₁₄ >= 0
x₁₅ >= 0
y₁ >= 0
y₂ >= 0
y₃ >= 0
y₄ >= 0

![image-20260728171951573](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728171951573.png)

### 连续投资

max  Z =  + 1.15x₄ + 1.28x₅ + 1.4x₆ + 1.06x₁₁

s.t.
  1x₁ + 1x₇ = 10

1x₂ + 1x₆ -1.06x₇ + 1x₈ = 0
 -1.15x₁ + 1x₃ + 1x₅  -1.06x₈ + 1x₉ = 0

-1.15x₂ + 1x₄ -1.06x₉ + 1x₁₀ = 0

-1.15x₃  -1.06x₁₀ + 1x₁₁ = 0
1x₁  -4y₁ >= 0
  1x₁  -10y₁ >= 0

1x₅  -5y₂ >= 0

1x₅  -3y₂ >= 0

1x₆ -2y₃ = 0

1y₃ <= 4

x₁ >= 0
x₂ >= 0
x₃ >= 0
x₄ >= 0
x₅ >= 0
x₆ >= 0
x₇ >= 0
x₈ >= 0
x₉ >= 0
x₁₀ >= 0
x₁₁ >= 0
y₁ >= 0
y₂ >= 0
y₃ >= 0



![image-20260728172916090](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728172916090.png)

## 运输问题

### 产销平衡

1800 1700 1550  3500 
1600 1500 1750  2500
3000 2000 1000

![image-20260728112505634](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728112505634.png)

### 产大于销

1800 1700 1550  3500

1600 1500 1750  2500

2500 1000 2000 

![image-20260728142042126](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728142042126.png)

###  销大于产

1800 1700 1550  3500

1600 1500 1750  2500

3000 1500 2000 

![image-20260728142151789](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728142151789.png)

### 指派问题

 12  10   9
 8    14   11
 7    13  16

![image-20260728144842890](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728144842890.png)

## 目标规划--需要明确的示例



## 网络规划

说明： 图片识别  嵌入了OCR/OpenCV这两个离线组件，是为了识别图片，但识别能力有限，如果不能识别，请手动完善矩阵或后期对接AI大模型别别

### 最短路问题

原图

![image-20260728213127815](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728213127815.png)

求解 黏贴|打开图片->离线识别

![image-20260728214702540](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728214702540.png)

![image-20260728215000591](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728215000591.png)

### 最小支撑树

  两村庄之间修建公路的费用(万元)

![image-20260728223345726](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728223345726.png)

![image-20260728225149716](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728225149716.png)

### 最大流问题

![image-20260728233916397](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728233916397.png)

```
1 2 60
1 3 30
1 4 40
1 5 20
2 6 40
3 6 50
3 7 40
4 7 30
4 8 60
5 8 30
6 9 30
7 9 40
8 9 50
```

![image-20260728233737872](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728233737872.png)

### 最小费用流

边表

```
1 4 999999 700
1 3 50 300
2 3 50 400
2 5 999999 900
3 4 50 200
3 5 50 400
```

供需

```
1 80
2 70
4 -90
5 -60
```

![image-20260728230408760](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260728230408760.png)

### 最小费最大流

```
1 2 6 6
1 4 6 3
2 5 3 4
2 3 2 5
4 3 3 2
4 6 1 3
3 5 2 4
3 6 2 3
6 7 4 4
5 7 5 7
4 7 2 8
```

![image-20260729002840667](C:\Users\39759\AppData\Roaming\Typora\typora-user-images\image-20260729002840667.png)

### 循环最短路--未找见相关例题



## 预测问题--未找见相关例题



# 选python 原因

**1. 科学计算库强大**

- `scipy.optimize.linprog` 直接求解线性规划，内置HiGHS求解器，精度高
- `pulp` 支持整数规划
- `numpy` 矩阵运算，灵敏度分析用到
- 这些在其他语言里要自己实现或找第三方

**2. 界面库tkinter内置**

- Python自带，不需要额外安装
- 够用，能做出原工具的表格样式

**3. 代码简洁**

- 同样功能，Python代码量比Java/C++少一半以上

**4. matplotlib画图**

- 可行域图、灵敏度图、排班图都靠它
- 几行代码出图

**5. 其他选择**

- 可通过源码转义成其他自己擅长的语言
