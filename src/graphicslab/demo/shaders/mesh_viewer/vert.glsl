#version 330

in vec3 in_vert;
in vec3 in_norm;

uniform vec4 base_color;
uniform mat4 mat_M;
uniform mat4 mat_V;
uniform mat4 mat_P;
uniform mat4 mat_MV;
uniform mat4 mat_MVP;

out vec4 vert_norm_world;
out vec4 vert_color;

void main() {
  vert_norm_world = mat_M * vec4(in_norm, 0);
  vert_color = base_color;
  gl_Position = mat_MVP * vec4(in_vert, 1);
}
