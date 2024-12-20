#version 330

in vec3 in_vert;

uniform mat4 mat_M;
uniform mat4 mat_V;
uniform mat4 mat_P;
uniform mat4 mat_MV;
uniform mat4 mat_MVP;

out vec4 vert_color;

void main() {
  vert_color = vec4(1, 0, 1, 1);
  gl_Position = mat_MVP * vec4(in_vert, 1);
}
