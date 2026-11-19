import torch


class LinearRegression(torch.nn.Module):
    def __init__(self, input_size, output_size):
        super().__init__()
        self.linear = torch.nn.Linear(input_size, output_size)

    def forward(self, x):
        return self.linear(x)


model = LinearRegression(4, 1)

x = torch.randn(3, 4)
y = torch.randn(3, 5)
z = x @ y
print(z.shape)
