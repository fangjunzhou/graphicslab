#version 330

in vec3 v_color;

layout(location = 0) out vec3 f_color;

void main() { f_color = v_color; }
